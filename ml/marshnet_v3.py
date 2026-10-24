"""Mash Plus V3 (legacy MarshNetV3 class): persistence-anchored residual ConvGRU, research-only.

Input history contains only previously acquired Sentinel images.  The optional
prior is derived from last observed month (NOT future target).  The learned
residual starts at zero, so the network initially behaves exactly as a soft
last-observation baseline. Missing prior observations produce uncertainty 0.5.
This architecture is deliberately smaller than enormous foundation models:
data coverage / labels are the present bottleneck.
"""
from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F
from marshnet_v2 import MarshNetV2

def prior_probability(history,wet_threshold=.10,ndvi_threshold=.30,epsilon=.01):
    """Historical water proxy; no target-frame pixels can enter this function."""
    if history.ndim!=5 or history.shape[2]!=7:
        raise ValueError("Expected raw [batch,history,7,height,width]")
    last=history[:,-1]
    available=last[:,6]>.5
    wet=(last[:,5]>wet_threshold)&(last[:,4]<ndvi_threshold)
    return torch.where(available,torch.where(wet,1.-epsilon,epsilon),.5).float()

class MarshNetV3(nn.Module):
    """Calibratable persistence logit + small spatio-temporal innovation.

    Notes: The V2 backbone is retained to make A/B comparison fair and to
    avoid untested exotic layers. Only the correction head changes.
    """
    def __init__(self,base=16,prior_epsilon=.01):
        super().__init__()
        self.backbone=MarshNetV2(base=base)
        self.prior_epsilon=float(prior_epsilon)
        if not 0<self.prior_epsilon<.1:raise ValueError("Invalid epsilon")
        # Initial exact match to the smoothed last-month baseline.
        nn.init.zeros_(self.backbone.head.weight)
        nn.init.zeros_(self.backbone.head.bias)
        self.residual_gain=nn.Parameter(torch.tensor(1.0))
        self.config={"model_name":"Mash Plus","model_version":"V3",
                     "architecture":"V3_persistence_residual_convgru_unet",
                     "base":base,"prior_epsilon":self.prior_epsilon,
                     "bands":["B03","B04","B08","B11","NDVI","MNDWI","VALID"]}
    def forward(self,normalized_history,prior):
        if prior.shape!=normalized_history.shape[:1]+normalized_history.shape[3:]:
            raise ValueError("Historical prior and input grid shapes differ")
        prior=prior.clamp(self.prior_epsilon,1-self.prior_epsilon)
        logits=torch.logit(prior)
        delta=6*torch.tanh(self.backbone(normalized_history)/6)
        return logits+self.residual_gain*delta

def masked_brier_bce(logits,labels,observed,bce_weight=.20,pos_weight=1.0):
    """Proper scoring rule with optional modest BCE; do not overweight rare wet."""
    mask=observed.float()
    n=mask.sum()
    if n<1:raise ValueError("No valid observed targets in batch")
    prob=torch.sigmoid(logits)
    brier=(((prob-labels)**2)*mask).sum()/n
    if not 1.0<=float(pos_weight)<=32.0:raise ValueError("Positive class BCE weight outside [1,32]")
    positive_weight=torch.as_tensor(pos_weight,dtype=logits.dtype,device=logits.device)
    bce=(F.binary_cross_entropy_with_logits(logits,labels,reduction="none",pos_weight=positive_weight)*mask).sum()/n
    return brier+bce_weight*bce

def masked_brier(probs,labels,mask):
    if mask.sum()==0:raise ValueError("No valid pixels")
    return (((probs-labels)**2)*mask).sum()/mask.sum()
