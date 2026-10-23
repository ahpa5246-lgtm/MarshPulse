#!/usr/bin/env python3
"""MarshNet Kaggle/CPU trainer. Real CSV required; no pretrained weights shipped."""
import argparse
import csv
import json
import math
import random
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from torch import nn

class MarshNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1=nn.Linear(5,12)
        self.fc2=nn.Linear(12,1)
    def forward(self,x):
        return self.fc2(torch.tanh(self.fc1(x))).squeeze(-1)

def load_csv(path):
    observations={};dates=set();h=w=0
    with open(path,encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if not {"date","row","col","water"}.issubset(reader.fieldnames or []):
            raise ValueError("Expected date,row,col,water")
        for row in reader:
            month=row["date"][:7]
            datetime.strptime(month,"%Y-%m")
            r=int(row["row"]);c=int(row["col"]);v=float(row["water"])
            if not 0<=r<100 or not 0<=c<100 or not math.isfinite(v) or not 0<=v<=1:
                raise ValueError("Invalid indices or water fraction")
            key=(month,r,c)
            if key in observations:raise ValueError("Duplicate month/cell")
            observations[key]=v;dates.add(month);h=max(h,r+1);w=max(w,c+1)
    dates=sorted(dates)
    if not 12<=len(dates)<=72 or h<3 or w<3 or h*w>4900:
        raise ValueError("Requires 12–72 months, 3x3–4900 cells")
    for prev,nxt in zip(dates,dates[1:]):
        year,month=map(int,prev.split("-"))
        if f"{year+(month==12):04d}-{month%12+1:02d}"!=nxt:
            raise ValueError("Missing month")
    if len(observations)!=len(dates)*h*w:raise ValueError("Missing cells")
    frames=np.empty((len(dates),h,w),dtype=np.float32)
    for t,month in enumerate(dates):
        for r in range(h):
            for c in range(w):
                frames[t,r,c]=observations[(month,r,c)]
    return dates,frames

def make_features(dates,frames):
    months,height,width=frames.shape
    xs=[];ys=[];bases=[]
    for t in range(1,months-1):
        m=int(dates[t][5:7])
        for r in range(height):
            for c in range(width):
                neighbor=[frames[t,rr,cc] for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1))
                          if 0<=rr<height and 0<=cc<width]
                current=float(frames[t,r,c])
                xs.append([current,float(frames[t-1,r,c]),float(np.mean(neighbor)),
                           math.sin(2*math.pi*m/12),math.cos(2*math.pi*m/12)])
                ys.append(float(frames[t+1,r,c]>=.5))
                bases.append(float(current>=.5))
    shape=(months-2,height*width)
    return (np.array(xs,np.float32).reshape(*shape,5),
            np.array(ys,np.float32).reshape(*shape),
            np.array(bases,np.float32).reshape(*shape))

def metrics(prob,truth):
    prediction=prob>=.5;positive=truth>=.5
    tp=int(np.sum(prediction&positive));fp=int(np.sum(prediction&~positive));fn=int(np.sum(~prediction&positive))
    return {"brier":float(np.mean((prob-truth)**2)),
            "f1":2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 1.,
            "accuracy":float(np.mean(prediction==positive)),
            "precision":tp/(tp+fp) if tp+fp else 0.,
            "recall":tp/(tp+fn) if tp+fn else 0.,
            "samples":int(len(truth))}

def run(args):
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(args.seed)
    dates,frames=load_csv(args.csv)
    x,y,b=make_features(dates,frames)
    n=len(dates);cut=max(8,int(n*.75));valstart=max(4,int((cut-1)*.82))
    # x index t-1, label from t+1. All boundaries are chronological.
    trainx=x[:valstart-1].reshape(-1,5);trainy=y[:valstart-1].reshape(-1)
    valx=x[valstart-1:cut-2].reshape(-1,5);valy=y[valstart-1:cut-2].reshape(-1)
    testx=x[cut-2:].reshape(-1,5);testy=y[cut-2:].reshape(-1);baseline=b[cut-2:].reshape(-1)
    if min(map(len,[trainx,valx,testx]))==0:raise ValueError("Empty train/val/holdout split")
    mean=trainx.mean(axis=0);std=np.maximum(.01,trainx.std(axis=0))
    norm=lambda a:(a-mean)/std
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model=MarshNet().to(device)
    optimizer=torch.optim.Adam(model.parameters(),lr=args.lr)
    loss_fn=nn.BCEWithLogitsLoss()
    tx=torch.tensor(norm(trainx),device=device);ty=torch.tensor(trainy,device=device)
    vx=torch.tensor(norm(valx),device=device);vy=torch.tensor(valy,device=device)
    test=torch.tensor(norm(testx),device=device)
    best=float("inf");best_epoch=0;best_state=None;patience=0;history=[]
    for epoch in range(1,args.epochs+1):
        model.train();order=torch.randperm(len(tx),device=device);total=0
        for indices in order.split(args.batch):
            optimizer.zero_grad(set_to_none=True)
            loss=loss_fn(model(tx[indices]),ty[indices])
            loss.backward();optimizer.step();total+=loss.item()*len(indices)
        model.eval()
        with torch.no_grad():p=torch.sigmoid(model(vx));val=float(torch.mean((p-vy)**2))
        history.append({"epoch":epoch,"trainLoss":total/len(tx),"validationBrier":val})
        print(f"epoch {epoch} training_loss={total/len(tx):.4f} validation_brier={val:.4f}",flush=True)
        if val<best-.00005:
            best=val;best_epoch=epoch;patience=0
            best_state={key:value.cpu().clone() for key,value in model.state_dict().items()}
        else:patience+=1
        if patience>=10:break
    if best_state is None:raise RuntimeError("No checkpoint")
    model.load_state_dict(best_state);model.eval()
    with torch.no_grad():probs=torch.sigmoid(model(test)).cpu().numpy()
    result={"model":metrics(probs,testy),"persistence":metrics(baseline,testy)}
    weights={k:best_state[k].numpy().flatten().tolist() for k in best_state}
    out=args.out;out.mkdir(parents=True,exist_ok=True)
    torch.save({"state_dict":best_state,"mean":mean.tolist(),"std":std.tolist(),
                "seed":args.seed,"best_epoch":best_epoch},out/"best.pt")
    artifact={
        "format":"marshnet-v1",
        "architecture":{"kind":"MLP","inputs":["water_t","water_tminus1","neighbor_mean_t","sin_month","cos_month"],
                        "input":5,"hidden":12,"output":1,"activation":"tanh/sigmoid"},
        "weights":{"W1":weights["fc1.weight"],"b1":weights["fc1.bias"],
                   "W2":weights["fc2.weight"],"b2":weights["fc2.bias"]},
        "normalization":{"mean":mean.tolist(),"std":std.tolist()},
        "training":{"seed":args.seed,"requestedEpochs":args.epochs,"completedEpochs":len(history),
                    "bestEpoch":best_epoch,"learningRate":args.lr,"batchSize":args.batch,
                    "trainSamples":len(trainx),"validationSamples":len(valx),"holdoutSamples":len(testx),
                    "trainingEnd":dates[valstart],"validationEnd":dates[cut-1],
                    "holdoutStart":dates[cut],"holdoutEnd":dates[-1],
                    "split":"chronological-with-internal-validation","history":history},
        "evaluation":result,
        "provenance":{"datasetName":args.csv.name,"origin":"imported_unverified","sourceVerified":False,
                      "firstMonth":dates[0],"lastMonth":dates[-1],
                      "grid":[int(frames.shape[2]),int(frames.shape[1])],"threshold":.5},
        "disclaimer":"Not independently verified as field truth. No hydraulic impact established."
    }
    (out/"marshnet.json").write_text(json.dumps(artifact,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"metrics.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print("CHECKPOINT:",out/"best.pt","BROWSER MODEL:",out/"marshnet.json",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--csv",type=Path,required=True)
    p.add_argument("--out",type=Path,default=Path("/kaggle/working/marshnet"))
    p.add_argument("--epochs",type=int,default=60)
    p.add_argument("--seed",type=int,default=42)
    p.add_argument("--batch",type=int,default=256)
    p.add_argument("--lr",type=float,default=.012)
    args=p.parse_args()
    if not 1<=args.epochs<=300 or not 1<=args.batch<=8192:p.error("Invalid epoch/batch size")
    run(args)
