#!/usr/bin/env python3
"""Mash Plus daily *continuation* training, with held-out geographic data excluded.

This script consumes a private training-only state bundle and never downloads or
inspects Hammar/Dalmaj test imagery. It persists the optimizer and weights across
Kaggle versions, but labels the model RESEARCH_ONLY until external validation.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,random,time
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader,ConcatDataset,WeightedRandomSampler
from marshnet_v3 import MarshNetV3,masked_brier_bce,masked_change_brier
from train_v3 import load_region,split,stats,History,val_score,aggregate_f1,training_sample_weights,predict
from change_diagnostics import transition_validation_report,aggregate_transition_reports
from paired_evidence import monthly_paired_brier_evidence

REGIONS=("hawizeh_train","central_train","sinnaf_train")
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def prepare_region_paths(root):
    root=Path(root)
    paths=[]
    for area in REGIONS:
        p=root/"source_imagery"/area/"hawizeh_s2_monthly.npz"
        if not p.is_file():raise ValueError(f"Missing trusted training region: {area}")
        paths.append(p)
    if any((root/"source_imagery"/x).exists() for x in ("dalmaj_spatial_test","hammar_spatial_test")):
        raise ValueError("Final geographic test data must NEVER be mounted into daily training")
    return paths
def metric_gate(brier,wet_f1,baseline_brier,baseline_f1,wet_pixels):
    """Thresholds frozen before daily attempts; validation-only screening."""
    return bool(wet_pixels>=25 and wet_f1 is not None and baseline_f1 is not None and
                brier<=baseline_brier*.98 and baseline_brier-brier>=.0005 and
                wet_f1>=baseline_f1+.02)
def validate_training_history(state,hashes,arch):
    if not isinstance(state,dict) or state.get("protocol")!="mash-plus-daily-v1":
        raise ValueError("Incompatible or missing persistent daily training state")
    if state.get("train_data_sha256")!=hashes:raise ValueError("Persistent checkpoint does not match input satellite arrays")
    if state.get("architecture")!=arch:raise ValueError("Architecture mismatch: refusing incompatible checkpoint")
    if state.get("training_days",0)<0:raise ValueError("Bad training-day counter")
    return state
def run(args):
    requested_minutes=float(getattr(args,"target_train_minutes",0.))
    if not 1<=args.epochs<=96 or args.batch<1 or not .0<args.lr<=.001 or not 0<=requested_minutes<=45:
        raise ValueError("Bound training to 96 epochs / 45 active-loop minutes per session")
    paths=prepare_region_paths(args.data)
    regions=[load_region(p,synthetic=args.synthetic_smoke) for p in paths]
    hashes=[r["sha"] for r in regions]
    mean,std=stats(regions,args.lookback)
    arch={"base":args.base,"lookback":args.lookback,"lr":args.lr,
          "wet_bce_ratio":3.0,"crop_size":32,"sampler_wet_boost":3.,
          "sampler_change_boost":3.,"model_class":"MarshNetV3"}
    seed=args.seed
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    if torch.cuda.is_available():torch.cuda.manual_seed_all(seed)
    device=torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    if device.type=="cuda":torch.backends.cudnn.benchmark=False
    torch.set_num_threads(min(torch.get_num_threads(),4))
    model=MarshNetV3(base=args.base).to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=args.lr,weight_decay=.01)
    previous=None
    if args.state_in and args.state_in.is_file():
        previous=torch.load(args.state_in,map_location="cpu",weights_only=True)
        validate_training_history(previous,hashes,arch)
        model.load_state_dict(previous["current_weights"])
        optimizer.load_state_dict(previous["optimizer_state"])
        for group in optimizer.param_groups:
            group["lr"]=args.lr
        start_days=int(previous["training_days"])
        total_epochs=int(previous["epochs_completed"])
        best_val=float(previous["best_validation_brier"])
        best_f1=float(previous["best_validation_f1"])
        best_weights=previous["best_weights"]
        best_optimizer_state=previous.get("best_optimizer_state")
        stagnant=int(previous.get("days_without_improvement",0))
    else:
        start_days=total_epochs=stagnant=0
        best_val=float("inf");best_f1=-1.0;best_weights=None
        best_optimizer_state=None
        # Optionally warm-start from a V4 research candidate; never assume it
        # passed the promotion gate. Optimizer begins fresh only on day zero.
        if args.v4_seed and args.v4_seed.is_file():
            initial=torch.load(args.v4_seed,map_location="cpu",weights_only=True)
            if initial.get("architecture") not in ("convgru","MarshNetV3"):
                raise ValueError("Wrong architecture in V4 seed checkpoint")
            if initial.get("lookback")!=args.lookback:raise ValueError("Lookback mismatch in V4 seed")
            model.load_state_dict(initial["state"])
    effective_lr=max(args.lr/16.,args.lr*(.5**(stagnant//3)))
    for param_group in optimizer.param_groups:
        param_group["lr"]=effective_lr
    # Preserve original support/prevalence. Neither validation nor test is
    # oversampled/cropped. Stratification is explicitly TRAIN ONLY.
    trains=[]
    for r in regions:
        tr,va,te=split(len(r["x"]),args.lookback)
        trains.append(History(r,tr,args.lookback,mean,std,augment=True,
                              crop_size=32,water_center_prob=.75,
                              water_margin=.025,ndvi_margin=.025))
    samples=ConcatDataset(trains)
    weights=training_sample_weights(regions,args.lookback,3.,3.)
    sampler=WeightedRandomSampler(torch.tensor(weights,dtype=torch.double),
        num_samples=len(samples)*2,replacement=True,
        generator=torch.Generator().manual_seed(seed+total_epochs))
    loader=DataLoader(samples,batch_size=args.batch,sampler=sampler,num_workers=0)
    history=[]
    training_loop_seconds=0.
    # A plateau does not authorize resetting architecture or test tuning.
    for epoch in range(args.epochs):
        if device.type=="cuda":torch.cuda.synchronize()
        epoch_started=time.monotonic()
        model.train();losses=[]
        for history_data,prior,label,mask in loader:
            history_data=history_data.to(device);prior=prior.to(device)
            label=label.to(device);mask=mask.to(device)
            if not mask.any():continue
            optimizer.zero_grad(set_to_none=True)
            logits=model(history_data,prior)
            loss=masked_brier_bce(logits,label,mask,pos_weight=3.)
            # Prior and last observed validity are derived from PAST inputs
            # only; target change is sampled from TRAIN months exclusively.
            loss=loss+masked_change_brier(
                logits,label,mask,prior,history_data[:,-1,6],strength=.20)
            if not torch.isfinite(loss):raise RuntimeError("Non-finite loss, no state exported")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
        if device.type=="cuda":torch.cuda.synchronize()
        epoch_training_seconds=time.monotonic()-epoch_started
        training_loop_seconds+=epoch_training_seconds
        if not losses:raise ValueError("No training target labels")
        brier,pred,reference=val_score(regions,args.lookback,mean,std,model,device,args.batch)
        candidate_f1=aggregate_f1(pred)
        reference_briers={name:sum(x[name]["brier"]*x[name]["evaluated_pixels"] for x in reference)/
                          sum(x[name]["evaluated_pixels"] for x in reference)
                          for name in ("persistence","smoothed_persistence","seasonal_12m")}
        baseline=min(reference_briers.values())
        reference_f1=max(aggregate_f1([r[name] for r in reference]) or 0.
                         for name in ("persistence","smoothed_persistence","seasonal_12m"))
        wet_pixels=sum(x["wet_truth_pixels"] for x in pred)
        improved=brier<best_val-1e-6 and (candidate_f1 is not None and candidate_f1>=best_f1-1e-6)
        if improved:
            best_val=float(brier);best_f1=float(candidate_f1)
            best_weights={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            best_optimizer_state=copy.deepcopy(optimizer.state_dict())
            stagnant=0
        history.append({"total_epoch":total_epochs+epoch+1,
                        "train_loop_seconds":round(epoch_training_seconds,3),
                        "train_loss":float(np.mean(losses)),
                        "validation_brier":float(brier),
                        "validation_wet_f1":candidate_f1,
                        "baseline_best_brier":baseline,
                        "baseline_best_wet_f1":reference_f1,
                        "validation_wet_pixels":wet_pixels,
                        "passed_promotion_gate":metric_gate(brier,candidate_f1,baseline,reference_f1,wet_pixels),
                        "best_model_renewed":improved})
        # Train for real measured forward/backward optimizer time; never
        # idle the GPU merely to hit a requested quota.
        if requested_minutes and len(history)>=2 and training_loop_seconds>=requested_minutes*60:
            break
    if not best_weights:raise ValueError("No valid improved model checkpoint")
    if not any(x["best_model_renewed"] for x in history):stagnant+=1
    # Read-only diagnosis of the validation-selected checkpoint: this metric
    # does not influence its selection and never inspects Hammar/Dalmaj.
    best_model=MarshNetV3(base=args.base).to(device)
    best_model.load_state_dict(best_weights)
    validation_events={}
    for name,region in zip(REGIONS,regions):
        _,validation_months,_=split(len(region["x"]),args.lookback)
        loader=DataLoader(History(region,validation_months,args.lookback,mean,std),
                          batch_size=args.batch,shuffle=False)
        probabilities=predict(best_model,loader,device)
        validation_events[name]=transition_validation_report(
            region["x"],region["dates"],validation_months,probabilities)
    change_summary=aggregate_transition_reports(validation_events)
    paired_brier_evidence=monthly_paired_brier_evidence(validation_events)
    rollback=False
    optimizer_reset=False
    if stagnant>=3:
        # Persist one coherent best-epoch model/optimizer pair. Old daily v1
        # checkpoints lack the historical best optimizer: reset explicitly.
        model.load_state_dict(best_weights)
        if best_optimizer_state is not None:
            optimizer.load_state_dict(copy.deepcopy(best_optimizer_state))
        else:
            optimizer=torch.optim.AdamW(model.parameters(),lr=effective_lr,weight_decay=.01)
            optimizer_reset=True
        rollback=True
    last=history[-1]
    run_date=str(getattr(args,"run_date","unknown"))
    prev_date=previous.get("last_run_date") if previous is not None else None
    previous_daily_minutes=float(previous.get("today_training_minutes",0.)) if (
        previous is not None and prev_date==run_date) else 0.
    today_training_minutes=previous_daily_minutes+training_loop_seconds/60.
    calendar_training_days=int(previous.get("calendar_training_days",start_days) if previous else 0)
    if previous is None or prev_date!=run_date:
        # First upgrade from a historical checkpoint has no last_run_date;
        # the legacy session number provides the conservative initial count.
        calendar_training_days+=1
    session_id=str(getattr(args,"session_id","legacy-unspecified"))
    completed_epochs=total_epochs+len(history)
    last=history[-1]
    state={"protocol":"mash-plus-daily-v1","model_name":"Mash Plus",
           "field_validated":False,"operationally_reliable":False,
           "train_data_sha256":hashes,"architecture":arch,
           "current_weights":{k:v.detach().cpu().clone() for k,v in model.state_dict().items()},
           "best_weights":best_weights,
           "best_optimizer_state":best_optimizer_state,
           "optimizer_state":optimizer.state_dict(),
           "best_validation_brier":best_val,"best_validation_f1":best_f1,
           "epochs_completed":completed_epochs,
           "training_days":start_days+1,
           "training_sessions":int(previous.get("training_sessions",start_days) if previous else 0)+1,
           "calendar_training_days":calendar_training_days,
           "last_run_date":run_date,"session_id":session_id,
           "today_training_minutes":today_training_minutes,
           "days_without_improvement":stagnant}
    args.out.mkdir(parents=True,exist_ok=True)
    torch.save(state,args.out/"daily_continuation_state.pt")
    report={"status":"RESEARCH_ONLY_NOT_FIELD_VALIDATED",
            "data_origin":"three real Sentinel-2 train AOIs",
            "geographic_test_used_for_training":False,
            "day_index":start_days+1,"source_commit":args.source_commit,
            "run_date_utc":run_date,
            "session_id":session_id,
            "session_index":state["training_sessions"],
            "calendar_training_days":calendar_training_days,
            "session_training_loop_minutes":round(training_loop_seconds/60.,3),
            "today_training_loop_minutes":round(today_training_minutes,3),
            "target_training_loop_minutes":requested_minutes,
            "target_reached":bool(requested_minutes and training_loop_seconds>=requested_minutes*60.),
            "daily_two_hour_target_reached":today_training_minutes>=120.,
            "epochs_this_session":len(history),
            "days_without_improvement":stagnant,
            "rollback_to_validation_best":rollback,
            "optimizer_reset_on_legacy_rollback":optimizer_reset,
            "effective_learning_rate":effective_lr,
            "epochs_completed":completed_epochs,
            "validation_history":history,
            "best_validation_brier":best_val,
            "best_validation_wet_f1":best_f1,
            "training_objective":"brier+weighted_bce+0.20_train_transition_brier",
            "confidence_masks_train_only":{"MNDWI":0.025,"NDVI":0.025},
            "paired_monthly_brier_evidence":paired_brier_evidence,
            "validation_change_diagnostics":{"aggregate":change_summary,
                                             "by_region":validation_events},
            "best_promoted_for_field_use":False,
            "can_claim_generalization":False,
            "next_action":"HOLD_AND_REVIEW" if stagnant>=5 else "CONTINUE_EXPERIMENTALLY"}
    (args.out/"daily_training_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("DAILY_CONTINUATION",json.dumps({k:v for k,v in report.items() if k!="validation_history"}),flush=True)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--state-in",type=Path)
    p.add_argument("--v4-seed",type=Path)
    p.add_argument("--epochs",type=int,default=2,help="Safety cap for completed epochs in one session")
    p.add_argument("--target-train-minutes",type=float,default=0.,help="Stop after measured train-loop wall time, or at max epochs; zero uses fixed epochs")
    p.add_argument("--session-id",default="legacy-unspecified")
    p.add_argument("--lookback",type=int,default=4)
    p.add_argument("--base",type=int,default=16)
    p.add_argument("--batch",type=int,default=2)
    p.add_argument("--seed",type=int,default=17)
    p.add_argument("--lr",type=float,default=.0001)
    p.add_argument("--source-commit",default="unknown")
    p.add_argument("--run-date",default="unknown")
    p.add_argument("--synthetic-smoke",action="store_true")
    p.add_argument("--cpu",action="store_true")
    args=p.parse_args();run(args)
if __name__=="__main__":main()
