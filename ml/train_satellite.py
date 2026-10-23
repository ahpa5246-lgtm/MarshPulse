#!/usr/bin/env python3
"""Train MarshNet V2 only from an explicit satellite NPZ. No synthetic fallback."""
import argparse,hashlib,json,random
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader
from marshnet_v2 import MarshNetV2,wet_pseudolabel,masked_bce_dice,evaluate_binary,BANDS
class Windows(Dataset):
    def __init__(self,cube,originals,targets,lookback,augment=False):
        self.cube=cube;self.originals=originals;self.targets=targets;self.lookback=lookback;self.augment=augment
    def __len__(self):return len(self.targets)
    def __getitem__(self,index):
        t=self.targets[index]
        x=torch.from_numpy(self.cube[t-self.lookback:t].copy())
        y,v=wet_pseudolabel(torch.from_numpy(self.originals[t]))
        if self.augment:
            if random.random()<.5:x=x.flip(-1);y=y.flip(-1);v=v.flip(-1)
            if random.random()<.5:x=x.flip(-2);y=y.flip(-2);v=v.flip(-2)
        return x,y,v,t
def split_targets(n,lookback):
    dates=list(range(lookback,n));a=int(len(dates)*.65);b=int(len(dates)*.80)
    parts=dates[:a],dates[a:b],dates[b:]
    if min(map(len,parts))<2:raise ValueError("Need at least two target months per split")
    return parts
def train(args):
    if not args.input.is_file():raise FileNotFoundError("Genuine input file missing: "+str(args.input))
    if not args.synthetic_smoke:
        manifest_path=args.input.with_name("satellite_manifest.json")
        if not manifest_path.is_file():raise FileNotFoundError("Missing satellite acquisition manifest; not treating unlabeled data as real satellite imagery")
        manifest=json.loads(manifest_path.read_text())
        if not sum(len(m.get("scenes",[])) for m in manifest.get("months",[])):
            raise ValueError("No authenticated-looking acquired scenes recorded in metadata")
    digest=hashlib.sha256(args.input.read_bytes()).hexdigest()
    with np.load(args.input,allow_pickle=False) as archive:
        cube=np.asarray(archive["x"],dtype=np.float32)
        dates=archive["dates"].tolist()
        bands=archive["bands"].tolist()
    if cube.ndim!=4 or cube.shape[1]!=7 or len(cube)<24 or len(dates)!=len(cube):
        raise ValueError("Expected >=24 monthly images [T,7,H,W]")
    if list(bands)!=list(BANDS):raise ValueError("Wrong channel names/order")
    if cube.shape[-1]%4 or cube.shape[-2]%4:raise ValueError("Image dimensions must be multiple of 4")
    if not np.isfinite(cube).all() or not np.isin(cube[:,6],[0,1]).all():raise ValueError("Invalid image/quality flags")
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    torch.set_num_threads(min(4,torch.get_num_threads()))
    tr,va,te=split_targets(len(cube),args.lookback)
    tr=[t for t in tr if cube[t,6].mean()>=args.min_valid]
    va=[t for t in va if cube[t,6].mean()>=args.min_valid]
    te=[t for t in te if cube[t,6].mean()>=args.min_valid]
    if min(map(len,(tr,va,te)))<2:raise ValueError("Insufficient *observed* months in one of the chronological splits")
    # No validation/test information used in normalization.
    observed=cube[:min(va),6]>.5;mean=[];std=[]
    for channel in range(6):
        vals=cube[:min(va),channel][observed]
        if not len(vals):raise ValueError("No training observations")
        mean.append(float(vals.mean()));std.append(max(float(vals.std()),.015))
    normalized=cube.copy()
    for k in range(6):
        normalized[:,k]=np.where(cube[:,6]>.5,(cube[:,k]-mean[k])/std[k],0.)
    sets=[Windows(normalized,cube,inds,args.lookback,i==0) for i,inds in enumerate([tr,va,te])]
    loaders=[DataLoader(s,batch_size=args.batch,shuffle=i==0,num_workers=0) for i,s in enumerate(sets)]
    device=torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    model=MarshNetV2(base=args.base).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=.01)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=args.epochs)
    best=float("inf");best_state=None;best_epoch=0;patience=0;history=[]
    for epoch in range(1,args.epochs+1):
        model.train();losses=[]
        for xb,yb,vb,_ in loaders[0]:
            xb,yb,vb=xb.to(device),yb.to(device),vb.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss=masked_bce_dice(model(xb),yb,vb);loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step();losses.append(loss.item())
        scheduler.step();model.eval();pp=[];yy=[];vv=[]
        with torch.no_grad():
            for xb,yb,vb,_ in loaders[1]:
                pp.append(model(xb.to(device)).sigmoid().cpu());yy.append(yb);vv.append(vb)
        metric=evaluate_binary(torch.cat(pp),torch.cat(yy),torch.cat(vv))
        history.append({"epoch":epoch,"train_loss":float(np.mean(losses)),"validation_brier":metric["brier"]})
        print(f"epoch={epoch} train_loss={np.mean(losses):.4f} val_brier={metric['brier']:.4f}",flush=True)
        if metric["brier"]<best-1e-4:
            best=metric["brier"];best_epoch=epoch;patience=0
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
        else:patience+=1
        if patience>=args.patience:break
    model.load_state_dict(best_state);model.eval()
    probs=[];truth=[];valid=[];baselines=[];fairm=[];periods=[]
    with torch.no_grad():
        for xb,yb,vb,ts in loaders[2]:
            probs.append(model(xb.to(device)).sigmoid().cpu());truth.append(yb);valid.append(vb)
            for j,t in enumerate(ts.tolist()):
                prior,prior_valid=wet_pseudolabel(torch.from_numpy(cube[t-1]))
                baselines.append(prior);fairm.append(prior_valid*vb[j]);periods.append(dates[t])
    p=torch.cat(probs);y=torch.cat(truth);v=torch.cat(valid);b=torch.stack(baselines);fair=torch.stack(fairm)
    report={"status":"SYNTHETIC SMOKE ONLY" if args.synthetic_smoke else "SATELLITE PROXY / UNVERIFIED LABELS",
            "label_definition":"MNDWI>0.1 and NDVI<0.3 from *future observed satellite images*; not field ground truth",
            "dataset_sha256":digest,"dates":dates,"test_months":periods,
            "split_targets":{"train":tr,"validation":va,"test":te},
            "model_test_all_valid":evaluate_binary(p,y,v),
            "model_same_pixels_as_baseline":evaluate_binary(p,y,fair),
            "persistence_same_pixels_as_model":evaluate_binary(b,y,fair),
            "best_epoch":best_epoch,"history":history,"params":sum(x.numel() for x in model.parameters()),
            "model_config":model.config,
            "limitations":["No field survey labels","One pilot location; no held-out region",
                           "Cloud censoring could bias scores","No real hydraulic intervention modeled"]}
    args.out.mkdir(parents=True,exist_ok=True)
    torch.save({"state":best_state,"config":model.config,"mean":mean,"std":std,
                "lookback":args.lookback,"source_sha256":digest,"epochs":best_epoch},args.out/"marshnet_v2.pt")
    (args.out/"evaluation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    np.savez_compressed(args.out/"test_predictions.npz",probabilities=p.numpy(),targets=y.numpy(),observed=v.numpy(),dates=np.asarray(periods))
    print("SAVED CHECKPOINT AND EVALUATION",args.out,flush=True)
    return report
def synthetic_smoke(path):
    # Explicitly opt-in test fixtures only. MUST NOT be reported as real imagery.
    a=np.zeros((24,7,32,32),np.float32)
    yy,xx=np.ogrid[:32,:32]
    for t in range(24):
        wet=(yy-16)**2+(xx-14-t//7)**2<(7+t%3)**2
        a[t,0]=np.where(wet,.19,.08);a[t,1]=np.where(wet,.06,.2)
        a[t,2]=np.where(wet,.02,.31);a[t,3]=np.where(wet,.003,.26)
        a[t,4]=np.where(wet,-.3,.25);a[t,5]=np.where(wet,.78,-.43);a[t,6]=1
    path.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(path,x=a,dates=np.asarray([f"{2023+t//12:04d}-{t%12+1:02d}" for t in range(24)]),bands=np.asarray(BANDS))
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path,default=Path("/kaggle/working/marshpulse/sentinel/hawizeh_s2_monthly.npz"))
    ap.add_argument("--out",type=Path,default=Path("/kaggle/working/marshpulse/training"))
    ap.add_argument("--epochs",type=int,default=24);ap.add_argument("--lookback",type=int,default=4)
    ap.add_argument("--batch",type=int,default=2);ap.add_argument("--base",type=int,default=32)
    ap.add_argument("--lr",type=float,default=.0002);ap.add_argument("--seed",type=int,default=42)
    ap.add_argument("--patience",type=int,default=8);ap.add_argument("--min-valid",type=float,default=.2)
    ap.add_argument("--cpu",action="store_true")
    ap.add_argument("--synthetic-smoke",action="store_true",help="Testing only; never evidence of real satellite accuracy")
    args=ap.parse_args()
    if args.epochs<1 or args.lookback<2 or args.base%8 or args.batch<1:ap.error("Bad hyperparameters")
    if args.synthetic_smoke:
        print("SYNTHETIC SMOKE ONLY — not satellite trained",flush=True)
        synthetic_smoke(args.input)
    train(args)
