"""Conservative, auditable quality gates for MarshNet V2 research.

All binary labels below are *satellite proxies*, not field ground truth.
Python/Numpy only; no random train/test mixing or hidden data substitution.
"""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

FEATURE_NAMES=("B03","B04","B08","B11","NDVI","MNDWI","VALID")

def wet_proxy(cube):
    """MNDWI/NDVI water *proxy*; only observed pixels can be called wet."""
    a=np.asarray(cube)
    if a.ndim!=4 or a.shape[1]!=7:
        raise ValueError("Expected T x 7 x H x W Sentinel monthly images")
    observed=a[:,6]>.5
    return (a[:,5]>.1)&(a[:,4]<.3)&observed,observed

def audit_cube(cube,dates=None,minimum_observed=.20):
    """Summarize observed water/no-water support rather than just accuracy."""
    x=np.asarray(cube)
    if not np.isfinite(x).all():raise ValueError("Non-finite Sentinel channel values")
    wet,observed=wet_proxy(x)
    if dates is not None and len(dates)!=len(x):raise ValueError("Date/image count mismatch")
    months=[]
    for i in range(len(x)):
        seen=int(observed[i].sum());water=int(wet[i].sum())
        months.append({"month":str(dates[i]) if dates is not None else str(i),
                       "observed_pixels":seen,"wet_pixels":water,
                       "wet_fraction_observed":water/seen if seen else None,
                       "observation_fraction":float(observed[i].mean())})
    valid=sum(m["observed_pixels"] for m in months)
    positives=sum(m["wet_pixels"] for m in months)
    return {
      "label_source":"UNVERIFIED Sentinel MNDWI/NDVI proxy — not surveyed water truth",
      "months":months,
      "total_observed_pixels":valid,
      "total_proxy_wet_pixels":positives,
      "overall_wet_fraction":positives/valid if valid else None,
      "months_with_wet_proxy":sum(m["wet_pixels"]>0 for m in months),
      "months_with_zero_wet_proxy":sum(m["observed_pixels"]>0 and m["wet_pixels"]==0 for m in months),
      "months_below_coverage":sum(m["observation_fraction"]<minimum_observed for m in months),
      "warnings":[
        *([] if positives else ["NO_WET_PIXELS: cannot learn wet detection from this pilot"]),
        *([] if valid and positives/max(valid,1)>=.01 else ["LOW_WET_PREVALENCE: accuracy may be misleading"]),
        *([] if sum(m["wet_pixels"]>0 for m in months)>=6 else ["FEW_WET_MONTHS: insufficient time variation for convincing validation"])
      ]
    }

def binary_metrics(probability,truth,mask):
    """Fair observed-pixel metrics; undefined wet-class F1 is NULL not success."""
    p=np.asarray(probability,dtype=np.float64)
    y=np.asarray(truth,dtype=np.float64)
    m=np.asarray(mask,dtype=bool)
    if p.shape!=y.shape or p.shape!=m.shape:raise ValueError("Metric arrays must align")
    if not m.any():return {"evaluated_pixels":0,"status":"NO_SHARED_OBSERVATIONS"}
    prob=p[m];true=y[m]>=.5
    if not np.isfinite(prob).all() or not np.isfinite(y[m]).all():
        raise ValueError("Non-finite prediction/label")
    if (prob<0).any() or (prob>1).any():raise ValueError("Probabilities outside [0,1]")
    predicted=prob>=.5
    tp=int((predicted & true).sum());fp=int((predicted & ~true).sum())
    fn=int((~predicted & true).sum());tn=int((~predicted & ~true).sum())
    positives=tp+fn; negatives=tn+fp;union=tp+fn+fp
    f1=2*tp/(2*tp+fp+fn) if positives else None
    balanced=(tp/positives+tn/negatives)/2 if positives and negatives else None
    return {"status":"OK" if positives and negatives else "ONE_CLASS_HOLDOUT",
            "evaluated_pixels":int(m.sum()),"wet_truth_pixels":positives,
            "wet_predicted_pixels":int(predicted.sum()),
            "wet_prevalence":positives/int(m.sum()),"brier":float(np.mean((prob-true)**2)),
            "precision":tp/(tp+fp) if tp+fp else None,
            "recall":tp/positives if positives else None,
            "f1":f1,"iou":tp/union if union else None,
            "accuracy":(tp+tn)/int(m.sum()),
            "balanced_accuracy":balanced,
            "confusion":{"tp":tp,"fp":fp,"fn":fn,"tn":tn}}

def benchmark_temporal(cube,test_indices,predictions):
    """Evaluate MarshNet, persistence, 12-month seasonality on IDENTICAL pixels.

    When a 12-month prior is unavailable, explicitly omit that target.
    This makes scores comparable rather than favoring any method with more data.
    """
    x=np.asarray(cube)
    wet,valid=wet_proxy(x)
    targets=list(map(int,test_indices))
    p=np.asarray(predictions,dtype=np.float64)
    if len(targets)!=len(p) or p.shape[1:]!=x.shape[2:]:
        raise ValueError("Predictions must match target months and image shape")
    if not targets or any(t<12 or t>=len(x) for t in targets):
        raise ValueError("Seasonal benchmarking requires targets >= 12")
    current=np.stack([wet[t] for t in targets])
    previous=np.stack([wet[t-1] for t in targets])
    seasonal=np.stack([wet[t-12] for t in targets])
    # Same observed pixels for all methods. The model itself can use history
    # with missing pixels, but must NOT get unfairly larger evaluation coverage.
    shared=np.stack([valid[t]&valid[t-1]&valid[t-12] for t in targets])
    evaluations={
        "model":binary_metrics(p,current,shared),
        "persistence":binary_metrics(previous.astype(float),current,shared),
        "seasonal_12m":binary_metrics(seasonal.astype(float),current,shared)
    }
    return {"fairness":"same target and observed pixels for all three methods",
            "test_indices":targets,
            "shared_observed_fraction":float(shared.mean()),
            "metrics":evaluations}

def readiness_verdict(benchmark,quality,has_independent_reference=False,has_spatial_holdout=False):
    """A good pilot score is not certification or validation for restoration."""
    mm=benchmark["metrics"]
    cur=mm["model"];pers=mm["persistence"];seas=mm["seasonal_12m"]
    baseline_scores=[m.get("brier") for m in (pers,seas) if m.get("brier") is not None]
    brier=cur.get("brier")
    beats=bool(baseline_scores and brier is not None and
               brier+1e-6<min(baseline_scores))
    support=cur.get("wet_truth_pixels",0)
    class_ok=cur.get("status")=="OK" and support>=25 and cur.get("wet_prevalence",0)>=.01
    scientific_validated=bool(beats and class_ok and has_independent_reference and has_spatial_holdout)
    reasons=[]
    if not beats:reasons.append("Model has not beaten BOTH persistence and 12-month seasonal reference Brier on shared observed pixels")
    if not class_ok:reasons.append("Insufficient balanced water/non-water examples in held-out observed pixels")
    if quality.get("warnings"):reasons+=quality["warnings"]
    if not has_independent_reference:reasons.append("No independent hand-annotated or field-verified water labels")
    if not has_spatial_holdout:reasons.append("No spatially held-out location")
    return {"status":"RESEARCH_PASS_NEEDS_FIELD_REVIEW" if scientific_validated else "NOT_VALIDATED",
            "beats_both_reference_baselines":beats,
            "adequate_test_wet_class":class_ok,
            "independent_reference":bool(has_independent_reference),
            "spatial_holdout":bool(has_spatial_holdout),
            "ready_for_operational_or_ecological_decisions":False,
            "reasons":reasons}

def main():
    import argparse
    pa=argparse.ArgumentParser(description="Audit real Sentinel monthly NPZ or explicit research fixture")
    pa.add_argument("--input",type=Path,required=True)
    pa.add_argument("--out",type=Path,required=True)
    args=pa.parse_args()
    with np.load(args.input,allow_pickle=False) as z:
        if z["bands"].tolist()!=list(FEATURE_NAMES):
            raise ValueError("Unexpected satellite channels")
        audit=audit_cube(z["x"],z["dates"].tolist())
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({k:v for k,v in audit.items() if k!="months"},indent=2))
if __name__=="__main__":main()
