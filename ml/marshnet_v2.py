"""MarshNet V2: satellite water-mask forecasting; not hydrological truth."""
import torch
from torch import nn
import torch.nn.functional as F
BANDS=("B03","B04","B08","B11","NDVI","MNDWI","VALID")
class Residual(nn.Module):
    def __init__(self,c,dropout=.12):
        super().__init__()
        self.net=nn.Sequential(nn.Conv2d(c,c,3,padding=1,bias=False),nn.GroupNorm(8,c),nn.SiLU(),nn.Dropout2d(dropout),nn.Conv2d(c,c,3,padding=1,bias=False),nn.GroupNorm(8,c))
    def forward(self,x):return F.silu(x+self.net(x))
class ConvGRUCell(nn.Module):
    def __init__(self,c):
        super().__init__()
        self.gates=nn.Conv2d(c*2,c*2,3,padding=1)
        self.candidate=nn.Conv2d(c*2,c,3,padding=1)
    def forward(self,x,h):
        if h is None:h=torch.zeros_like(x)
        z,r=self.gates(torch.cat([x,h],1)).chunk(2,1)
        z,r=z.sigmoid(),r.sigmoid()
        n=torch.tanh(self.candidate(torch.cat([x,r*h],1)))
        return (1-z)*h+z*n
class MarshNetV2(nn.Module):
    """Residual CNN + 2-layer ConvGRU + skip decoder. Input [B,T,7,H,W]."""
    def __init__(self,base=32,in_channels=7,dropout=.12):
        super().__init__()
        if base%8:raise ValueError("base must be a multiple of 8")
        self.stem=nn.Sequential(nn.Conv2d(in_channels,base,3,padding=1),nn.GroupNorm(8,base),nn.SiLU(),Residual(base,dropout))
        self.enc1=nn.Sequential(nn.Conv2d(base,base*2,3,stride=2,padding=1),nn.GroupNorm(8,base*2),nn.SiLU(),Residual(base*2,dropout))
        self.enc2=nn.Sequential(nn.Conv2d(base*2,base*4,3,stride=2,padding=1),nn.GroupNorm(8,base*4),nn.SiLU(),Residual(base*4,dropout))
        self.temporal1=ConvGRUCell(base*4)
        self.temporal2=ConvGRUCell(base*4)
        self.dec1=nn.Sequential(nn.Conv2d(base*6,base*2,3,padding=1),nn.GroupNorm(8,base*2),nn.SiLU(),Residual(base*2,dropout))
        self.dec0=nn.Sequential(nn.Conv2d(base*3,base,3,padding=1),nn.GroupNorm(8,base),nn.SiLU(),Residual(base,dropout))
        self.head=nn.Conv2d(base,1,1)
        self.config={"base":base,"in_channels":in_channels,"dropout":dropout}
    def forward(self,x):
        if x.ndim!=5 or x.shape[2]!=7:raise ValueError("Expected [batch,time,7,height,width]")
        if x.shape[-1]%4 or x.shape[-2]%4:raise ValueError("Spatial dimensions must be multiples of four")
        h1=h2=None
        for t in range(x.shape[1]):
            skip0=self.stem(x[:,t]);skip1=self.enc1(skip0);z=self.enc2(skip1)
            h1=self.temporal1(z,h1);h2=self.temporal2(h1,h2)
        x1=F.interpolate(h2,size=skip1.shape[-2:],mode="bilinear",align_corners=False)
        x1=self.dec1(torch.cat([x1,skip1],1))
        x0=F.interpolate(x1,size=skip0.shape[-2:],mode="bilinear",align_corners=False)
        return self.head(self.dec0(torch.cat([x0,skip0],1))).squeeze(1)
def wet_pseudolabel(image):
    """Future-image MNDWI>0.1, NDVI<0.3; NOT independent field truth."""
    valid=image[6]>.5
    return ((image[5]>.1)&(image[4]<.3)&valid).float(),valid.float()
def masked_bce_dice(logits,target,mask):
    mask=mask.float()
    if not mask.any():return logits.sum()*0
    bce=F.binary_cross_entropy_with_logits(logits,target,reduction="none")
    bce=(bce*mask).sum()/mask.sum().clamp_min(1)
    p=logits.sigmoid()*mask;y=target*mask
    return bce+.45*(1-(2*(p*y).sum()+1)/(p.sum()+y.sum()+1))
@torch.no_grad()
def evaluate_binary(probs,ys,valid):
    probs=probs[valid>.5].float();ys=ys[valid>.5].float()
    if not len(probs):raise ValueError("No valid observed targets to evaluate")
    pred=probs>=.5;truth=ys>=.5
    tp=(pred&truth).sum().item();fp=(pred&~truth).sum().item();fn=(~pred&truth).sum().item()
    return {"brier":((probs-ys)**2).mean().item(),"f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,"iou":tp/(tp+fp+fn) if tp+fp+fn else 1.,"accuracy":(pred==truth).float().mean().item(),"n_valid_pixels":int(len(probs)),"wet_truth_fraction":truth.float().mean().item(),"wet_prediction_fraction":pred.float().mean().item(),"true_positive_pixels":int(truth.sum().item())}
