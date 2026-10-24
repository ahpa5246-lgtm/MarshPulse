"""Unbiased, validation-only wetland CHANGE diagnostics for Mash Plus.

Measures gain, drying and unchanged-water pixels on exactly the same naturally
observed grids as the seasonal baseline. These metrics are satellite water
PROXY diagnostics, not ecological ground truth or a new training label.
"""
from __future__ import annotations
import numpy as np
from quality_gate import wet_proxy

def _ratio(n,d):
    return float(n/d) if d else None

def _safe_brier(p,y,mask):
    return float(np.mean((p[mask]-y[mask])**2)) if mask.any() else None

def _f1(tp,fp,fn):
    return _ratio(2*tp,2*tp+fp+fn)

def transition_validation_report(cube,dates,targets,predictions,confidence_band=.05):
    x=np.asarray(cube,dtype=np.float32)
    if not 0<=confidence_band<=.2:
        raise ValueError("Confidence band must remain within [0,0.2]")
    targets=list(targets)
    probs=np.asarray(predictions,dtype=np.float64)
    if x.ndim!=4 or x.shape[1]!=7 or len(dates)!=len(x):
        raise ValueError("Expected aligned [months,7,H,W] satellite cube")
    if probs.shape!=(len(targets),*x.shape[-2:]):
        raise ValueError("One prediction map required per validation target month")
    if not np.isfinite(probs).all() or (probs<0).any() or (probs>1).any():
        raise ValueError("Bad probability maps")
    if not targets or min(targets)<12 or max(targets)>=len(x):
        raise ValueError("Targets must have previous month and seasonal reference")
    if targets!=sorted(set(targets)):
        raise ValueError("Targets must be chronological and unique")
    wet,observed=wet_proxy(x)
    months=[]
    totals={key:0 for key in ("observed_pixels","wet_gain_pixels","drying_pixels",
              "stable_pixels","uncertain_target_pixels","transition_tp",
              "transition_fp","transition_fn","correct_water_gains",
              "correct_drying","gain_predictions","drying_predictions")}
    loss={key:0. for key in ("change_model","change_persistence",
                               "stable_model","stable_persistence",
                               "clear_label_model","clear_label_persistence")}
    count={key:0 for key in loss}
    for i,t in enumerate(targets):
        shared=observed[t]&observed[t-1]&observed[t-12]
        previous=wet[t-1]
        truth=wet[t]
        model_wet=probs[i]>=.5
        predicted_change=(model_wet^previous)&shared
        actual_change=(truth^previous)&shared
        gain=(~previous)&truth&shared
        drying=previous&(~truth)&shared
        stable=shared&~actual_change
        # Diagnostic only: label sensitivity is measured on FUTURE target band,
        # but is never passed to the neural model or its inputs.
        uncertain=(np.abs(x[t,5]-.1)<confidence_band |
                   (np.abs(x[t,4]-.3)<.03))&shared
        confident=shared&~uncertain
        tp=int((predicted_change&actual_change).sum())
        fp=int((predicted_change&~actual_change).sum())
        fn=int((~predicted_change&actual_change).sum())
        values={
            "observed_pixels":int(shared.sum()),
            "wet_gain_pixels":int(gain.sum()),
            "drying_pixels":int(drying.sum()),
            "stable_pixels":int(stable.sum()),
            "uncertain_target_pixels":int(uncertain.sum()),
            "transition_tp":tp,"transition_fp":fp,"transition_fn":fn,
            "correct_water_gains":int((model_wet&gain).sum()),
            "correct_drying":int(((~model_wet)&drying).sum()),
            "gain_predictions":int(((~previous)&model_wet&shared).sum()),
            "drying_predictions":int((previous&(~model_wet)&shared).sum())}
        prev_soft=np.where(previous,.99,.01).astype(np.float64)
        month={"month":str(dates[t]),**values}
        for region_name,mask in (("change",actual_change),("stable",stable),("clear_label",confident)):
            for who,p in (("model",probs[i]),("persistence",prev_soft)):
                key=f"{region_name}_{who}"
                brier=_safe_brier(p,truth,mask)
                month[f"{key}_brier"]=brier
                if brier is not None:
                    n=int(mask.sum());count[key]+=n;loss[key]+=brier*n
        months.append(month)
        for key,value in values.items():totals[key]+=value
    result={"source":"Sentinel-derived satellite water proxy, not field truth",
            "months":months,
            "months_evaluated":sum(m["observed_pixels"]>0 for m in months),
            "total_counts":totals,
            "observed_change_fraction":_ratio(totals["wet_gain_pixels"]+totals["drying_pixels"],
                                              totals["observed_pixels"]),
            "gain_detection_recall":_ratio(totals["correct_water_gains"],totals["wet_gain_pixels"]),
            "drying_detection_recall":_ratio(totals["correct_drying"],totals["drying_pixels"]),
            "predicted_transition_precision":_ratio(totals["transition_tp"],
                                                       totals["transition_tp"]+totals["transition_fp"]),
            "transition_recall":_ratio(totals["transition_tp"],
                                       totals["transition_tp"]+totals["transition_fn"]),
            "transition_f1":_f1(totals["transition_tp"],totals["transition_fp"],
                               totals["transition_fn"]),
            "brier_by_subset":{key:_ratio(loss[key],count[key]) for key in loss},
            "note":"Proxy labels are threshold-sensitive; nearby months and pixels are correlated. Results do not certify field reliability."}
    return result

def aggregate_transition_reports(per_region):
    if not per_region:raise ValueError("No validation regions")
    totals={}
    nregions=0
    month_count=0
    for region,report in per_region.items():
        if not isinstance(report,dict) or "total_counts" not in report:
            raise ValueError("Missing region transition report")
        nregions+=1
        month_count+=report["months_evaluated"]
        for key,value in report["total_counts"].items():totals[key]=totals.get(key,0)+int(value)
    return {"regions":nregions,"region_names":list(per_region),
            "months_evaluated":month_count,"total_counts":totals,
            "wet_gain_recall":_ratio(totals["correct_water_gains"],totals["wet_gain_pixels"]),
            "drying_recall":_ratio(totals["correct_drying"],totals["drying_pixels"]),
            "transition_f1":_f1(totals["transition_tp"],totals["transition_fp"],
                                totals["transition_fn"]),
            "transition_fraction":_ratio(totals["wet_gain_pixels"]+totals["drying_pixels"],
                                         totals["observed_pixels"]),
            "reference":"satellite proxy only",
            "field_validated":False}
