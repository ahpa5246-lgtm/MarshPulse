#!/usr/bin/env python3
"""MarshNet V3 challenger / baseline champion-selection on real satellite data.

Comparable observed-pixel scores. Chronological model selection, entire-region
spatial holdout, immutable SHA, deterministic seeds. No test-set tuning.
All image-derived MNDWI labels remain UNVERIFIED (not field-truth).
"""
import argparse,copy,hashlib,json,random
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import Dataset,DataLoader,ConcatDataset
from marshnet_v2 import BANDS
from marshnet_v3 import MarshNetV3,masked_brier_bce
from quality_gate import benchmark_temporal,wet_proxy

def next_month(date):
    y,m=map(int,date.split("-"));return f"{y+(m==12):04d}-{m%12+1:02d}"

def load_region(path, synthetic=False):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    with np.load(path,allow_pickle=False) as f:
        x=np.asarray(f["x"],dtype=np.float32)
        dates=list(map(str,f["dates"].tolist()))
        bands=f["bands"].tolist()
    if x.ndim!=4 or x.shape[1]!=7 or x.shape[-1]%4 or x.shape[-2]%4 or len(x)<24:
        raise ValueError("Need >=24 monthly [T,7,H,W] images aligned to grid")
    if bands!=list(BANDS) or not np.isfinite(x).all() or not np.isin(x[:,6],[0,1]).all():
        raise ValueError("Bad satellite band schema, nonfinite pixels or validity mask")
    if dates!=sorted(set(dates)) or any(next_month(a)!=b for a,b in zip(dates,dates[1:])):
        raise ValueError("Missing/duplicated/unsorted monthly timestamps")
    manifest_path=path.with_name("satellite_manifest.json")
    if not synthetic:
        if not manifest_path.exists():raise ValueError("Missing real acquisition manifest")
        m=json.loads(manifest_path.read_text(encoding="utf8"))
        if not m.get("source","").startswith("REAL ESA Sentinel-2") or len(m.get("months",[]))!=len(x):
            raise ValueError("Not a real Sentinel acquisition manifest")
        if [d["month"] for d in m["months"]]!=dates or any(not d["scenes"] for d in m["months"]):
            raise ValueError("Missing month metadata or actual scene references")
        bbox=m.get("bbox_lonlat")
        if not isinstance(bbox,list) or len(bbox)!=4:raise ValueError("Missing AOI bbox")
    else:
        bbox=None
    return {"x":x,"dates":dates,"bbox":bbox,"sha":sha,"path":str(path),"synthetic":synthetic}

def disjoint_bbox(a,b):
    """Conservative: touching adjacent edge is allowed; overlapping is not."""
    if a is None or b is None:return False
    return a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1]

def split(n,lookback):
    months=list(range(max(lookback,12),n))
    cut1=int(len(months)*.66);cut2=int(len(months)*.82)
    tr,va,te=months[:cut1],months[cut1:cut2],months[cut2:]
    if min(map(len,(tr,va,te)))<2:
        raise ValueError("Not enough complete months for three chronological splits")
    return tr,va,te

def stats(regions,lookback):
    vals=[[] for _ in range(6)]
    for region in regions:
        tr,_,_=split(len(region["x"]),lookback)
        # Target t only uses [t-lookback ... t-1]; no future month admitted.
        prefix=region["x"][:max(tr)]
        mask=prefix[:,6]>.5
        for i in range(6):vals[i].append(prefix[:,i][mask])
    mean=np.array([np.concatenate(v).mean() for v in vals],dtype=np.float32)
    std=np.array([max(.015,float(np.concatenate(v).std())) for v in vals],dtype=np.float32)
    return mean,std

class History(Dataset):
    def __init__(self,region,targets,lookback,mean,std,augment=False):
        self.original=region["x"];self.targets=targets
        self.lookback=lookback;self.mean=mean;self.std=std;self.augment=augment
    def __len__(self):return len(self.targets)
    def __getitem__(self,i):
        t=self.targets[i]
        past=self.original[t-self.lookback:t].copy()
        prior_wet=(past[-1,5]>.1)&(past[-1,4]<.3)
        prior=np.where(past[-1,6]>.5,np.where(prior_wet,.99,.01),.5).astype(np.float32)
        normalized=past.copy()
        for c in range(6):
            normalized[:,c]=np.where(past[:,6]>.5,(past[:,c]-self.mean[c])/self.std[c],0.)
        current=self.original[t]
        label=((current[5]>.1)&(current[4]<.3)&(current[6]>.5)).astype(np.float32)
        observed=(current[6]>.5).astype(np.float32)
        if self.augment:
            if random.random()<.5:
                normalized=normalized[...,::-1];prior=prior[...,::-1]
                label=label[...,::-1];observed=observed[...,::-1]
            if random.random()<.5:
                normalized=normalized[...,::-1,:];prior=prior[::-1,:]
                label=label[::-1,:];observed=observed[::-1,:]
        return tuple(torch.from_numpy(np.ascontiguousarray(a)) for a in (normalized,prior,label,observed))

@torch.no_grad()
def predict(net,loader,device):
    net.eval();output=[]
    for x,prior,_,_ in loader:
        logits=net(x.to(device),prior.to(device)).float()
        output.append(logits.sigmoid().cpu().numpy())
    return np.concatenate(output)

def benchmark(region,targets,preds):
    return benchmark_temporal(region["x"],targets,preds)

def val_score(regions,lookback,mean,std,net,device,batch):
    weighted=0.;n=0
    allpred=[];allbaselines=[]
    for region in regions:
        _,va,_=split(len(region["x"]),lookback)
        loader=DataLoader(History(region,va,lookback,mean,std),batch_size=batch)
        prob=predict(net,loader,device)
        scores=benchmark(region,va,prob)["metrics"]
        match=scores["model"].get("evaluated_pixels",0)
        if match:
            weighted+=scores["model"]["brier"]*match;n+=match
        allpred.append(scores["model"]);allbaselines.append(scores["persistence"])
    if not n:raise ValueError("No observed validation targets")
    return weighted/n,allpred,allbaselines

def run(args):
    if args.lookback<2 or args.base%8 or args.epochs<1 or args.batch<1:
        raise ValueError("Invalid training parameters")
    regions=[load_region(p,args.synthetic_smoke) for p in args.train_input]
    spatial=load_region(args.spatial_test_input,args.synthetic_smoke) if args.spatial_test_input else None
    if spatial and not all(disjoint_bbox(r["bbox"],spatial["bbox"]) for r in regions):
        if not args.synthetic_smoke:raise ValueError("Spatial holdout AOI overlaps training AOI")
    if spatial and any(r["sha"]==spatial["sha"] for r in regions):
        raise ValueError("Holdout data archive cannot also be training archive")
    if len({r["sha"] for r in regions})!=len(regions):raise ValueError("Repeated training dataset")
    mean,std=stats(regions,args.lookback)
    seeds=[int(x) for x in args.seeds.split(",")]
    if not seeds or len(seeds)>5 or len(set(seeds))!=len(seeds):raise ValueError("Choose 1–5 distinct seeds")
    device=torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    if device.type=="cuda":torch.backends.cudnn.benchmark=False
    torch.set_num_threads(min(4,torch.get_num_threads()))
    trains=[]
    for region in regions:
        tr,_,_=split(len(region["x"]),args.lookback)
        trains.append(History(region,tr,args.lookback,mean,std,augment=True))
    loader=DataLoader(ConcatDataset(trains),batch_size=args.batch,shuffle=True,num_workers=0)
    candidates=[];best_weights=None;best_val=float("inf");best_seed=None
    for seed in seeds:
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
        net=MarshNetV3(base=args.base).to(device)
        optimizer=torch.optim.AdamW(net.parameters(),lr=args.lr,weight_decay=.01)
        patience=0;local_best=float("inf");local_state=None;local_epoch=0
        history=[]
        for epoch in range(1,args.epochs+1):
            net.train();losses=[]
            for x,prior,y,mask in loader:
                x=x.to(device);prior=prior.to(device);y=y.to(device);mask=mask.to(device)
                optimizer.zero_grad(set_to_none=True)
                loss=masked_brier_bce(net(x,prior),y,mask)
                if not torch.isfinite(loss):raise RuntimeError("Nonfinite training loss")
                loss.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(),1.0);optimizer.step()
                losses.append(float(loss))
            score,_,_=val_score(regions,args.lookback,mean,std,net,device,args.batch)
            history.append({"epoch":epoch,"train_loss":float(np.mean(losses)),"validation_shared_brier":score})
            print(f"seed={seed} epoch={epoch} train={np.mean(losses):.5f} val={score:.5f}",flush=True)
            if score<local_best-1e-5:
                local_best=score;local_epoch=epoch
                local_state={k:v.detach().cpu().clone() for k,v in net.state_dict().items()}
                patience=0
            else:patience+=1
            if patience>=args.patience:break
        net.load_state_dict(local_state)
        score,pred_stats,baseline_stats=val_score(regions,args.lookback,mean,std,net,device,args.batch)
        baseline_brier=sum(s["brier"]*s["evaluated_pixels"] for s in baseline_stats)/sum(s["evaluated_pixels"] for s in baseline_stats)
        # Gate is precommitted: val improvement plus non-empty wet support.
        supports=sum(s["wet_truth_pixels"] for s in pred_stats)
        passed=bool(supports>=args.min_wet_valid and score+1e-5<baseline_brier)
        candidates.append({"seed":seed,"best_epoch":local_epoch,"val_brier":score,
                           "val_persistence_brier":baseline_brier,"validation_wet_pixels":supports,
                           "passed_validation_gate":passed,"history":history})
        if passed and score<best_val:
            best_val=score;best_weights=copy.deepcopy(local_state);best_seed=seed
    chosen={"type":"MarshNetV3" if best_weights else "PERSISTENCE_BASELINE",
            "selection_method":"validation only, no test score used",
            "seed":best_seed,"validation_challengers":candidates,
            "model_never_authorized_for_field_decisions":True}
    checkpoints={}
    if best_weights:
        best_model=MarshNetV3(base=args.base).to(device)
        best_model.load_state_dict(best_weights);best_model.eval()
    evaluations=[]
    for name,region in [(f"train_aoi_{i}",r) for i,r in enumerate(regions)]+([("spatial_holdout",spatial)] if spatial else []):
        ids=split(len(region["x"]),args.lookback)[2] if name!="spatial_holdout" else list(range(max(12,args.lookback),len(region["x"])))
        if best_weights:
            inputs=DataLoader(History(region,ids,args.lookback,mean,std),batch_size=args.batch)
            probs=predict(best_model,inputs,device)
        else:
            wet,valid=wet_proxy(region["x"])
            probs=np.stack([np.where(valid[t-1],np.where(wet[t-1],.99,.01),.5) for t in ids]).astype(np.float32)
        score=benchmark(region,ids,probs)
        score["region"]=name;score["data_sha256"]=region["sha"]
        score["has_spatial_holdout"]=name=="spatial_holdout"
        evaluations.append(score)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if best_weights:
        torch.save({"state":best_weights,"architecture":"MarshNetV3",
                   "config":best_model.config,"mean":mean.tolist(),"std":std.tolist(),
                   "lookback":args.lookback,"seed":best_seed,
                   "dataset_sha256":[r["sha"] for r in regions],"field_validated":False},
                  out/"marshnet_v3_challenger.pt")
    report={"status":"SYNTHETIC TEST ONLY" if args.synthetic_smoke else "REAL SATELLITE PROXY / NO FIELD VALIDATION",
      "architecture":"persistence-residual ConvGRU U-Net",
      "normalization_fit":"training input months only",
      "data_provenance":[{"path":r["path"],"sha256":r["sha"],"bbox":r["bbox"]} for r in regions],
      "spatial_test_provenance":{"path":spatial["path"],"sha256":spatial["sha"],"bbox":spatial["bbox"]} if spatial else None,
      "device":str(device),"selected_champion":chosen,"test_evaluations":evaluations,
      "operationally_reliable":False,"independent_field_labels":False,
      "spatial_transfer_evaluated":spatial is not None,
      "limitations":["Satellite-derived water pseudo-label is not independent reference truth",
                     "No flow, discharge, water quality or restoration physics evaluated",
                     "No operational model authorized; challenger selection requires field review"]}
    (out/"v3_evaluation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print("CHAMPION",chosen["type"],"field validated FALSE",flush=True)
    return report

def smoke_data(target):
    from marshnet_v2 import BANDS
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    n=28;s=32
    cube=np.zeros((n,7,s,s),np.float32)
    yy,xx=np.ogrid[:s,:s]
    for t in range(n):
        wet=(yy-15)**2+(xx-15-(t%5))**2<(6+t%3)**2
        cube[t,4]=np.where(wet,-.2,.2);cube[t,5]=np.where(wet,.7,-.3)
        cube[t,6]=1.
    dates=np.asarray([f"{2024+t//12:04d}-{t%12+1:02d}" for t in range(n)])
    np.savez_compressed(target,x=cube,dates=dates,bands=np.asarray(BANDS))

def cli():
    p=argparse.ArgumentParser()
    p.add_argument("--train-input",type=Path,action="append",required=True)
    p.add_argument("--spatial-test-input",type=Path)
    p.add_argument("--out",type=Path,default=Path("/kaggle/working/marshpulse-v3"))
    p.add_argument("--epochs",type=int,default=24);p.add_argument("--patience",type=int,default=6)
    p.add_argument("--batch",type=int,default=2);p.add_argument("--lookback",type=int,default=4)
    p.add_argument("--base",type=int,default=16);p.add_argument("--lr",type=float,default=.00015)
    p.add_argument("--seeds",default="17,42,2026")
    p.add_argument("--min-wet-valid",type=int,default=25)
    p.add_argument("--cpu",action="store_true")
    p.add_argument("--synthetic-smoke",action="store_true")
    args=p.parse_args()
    if args.synthetic_smoke:
        for item in args.train_input:smoke_data(item)
        if args.spatial_test_input:smoke_data(args.spatial_test_input)
    run(args)
if __name__=="__main__":cli()
