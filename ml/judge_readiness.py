#!/usr/bin/env python3
"""Fail-closed research credibility audit for Mash Plus V3 experiment evidence.

This does not certify a model. It only checks whether the held-out satellite
proxy experiment justifies an honest, limited research claim.
"""
import argparse
import json
import math
from pathlib import Path

BASELINES=("persistence","smoothed_persistence","seasonal_12m")

def _finite_number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)

def audit(report):
    reasons=[]
    def require(condition,message):
        if not condition:reasons.append(message)
    if not isinstance(report,dict):
        return {"model":"Mash Plus V3","status":"NOT_DEMONSTRATED",
                "reasons":["Evaluation must be a JSON object"]}
    require(report.get("model_name")=="Mash Plus" and report.get("model_version")=="V3",
            "Wrong or missing model identity")
    require(report.get("status")=="REAL SATELLITE PROXY / NO FIELD VALIDATION",
            "No verified real-satellite research provenance (synthetic or missing)")
    training=report.get("data_provenance")
    require(isinstance(training,list) and len(training)>=2,
            "At least two independently acquired training regions are required")
    if isinstance(training,list):
        require(all(isinstance(x,dict) and len(str(x.get("sha256","")))==64 and
                    len(str(x.get("manifest_sha256","")))==64
                    for x in training),"Training arrays and acquisition manifests need SHA-256")
        require(len({str(x.get("sha256")) for x in training if isinstance(x,dict)})==len(training),
                "Repeated training archive")
    holdout=report.get("spatial_test_provenance")
    require(isinstance(holdout,dict) and len(str(holdout.get("sha256","")))==64
            if isinstance(holdout,dict) else False,
            "Independent spatial-holdout provenance not recorded")
    require(report.get("spatial_transfer_evaluated") is True,
            "No sealed spatial transfer evaluation")
    require(report.get("evaluated_neural_checkpoint")=="VALIDATION_PASSED_RESEARCH_ONLY",
            "Evaluated checkpoint is not a traceable validation-passed neural model")
    champion=report.get("selected_champion") or {}
    require(isinstance(champion,dict) and champion.get("type")=="Mash Plus V3",
            "Neural challenger was not chosen by chronological validation")
    trials=champion.get("validation_challengers",[]) if isinstance(champion,dict) else []
    require(isinstance(trials,list) and len(trials)>=2 and
            any(isinstance(x,dict) and x.get("passed_validation_gate") for x in trials),
            "No multi-seed validation run passed the Brier AND wet-F1 promotion gates")
    scores=report.get("test_evaluations")
    spatial=next((x for x in scores
                  if isinstance(x,dict) and x.get("region")=="spatial_holdout"),None) if isinstance(scores,list) else None
    require(spatial is not None,"No geographically held-out final scores")
    summary={"model":"Mash Plus V3","spatial_holdout_metrics":{},
             "independent_field_labels":report.get("independent_field_labels") is True,
             "field_or_operational_claim_permitted":False,
             "reasons":reasons}
    if isinstance(spatial,dict):
        metrics=spatial.get("metrics")
        if not isinstance(metrics,dict):
            reasons.append("No spatial-holdout metrics dictionary")
        else:
            present=all(k in metrics and isinstance(metrics[k],dict) for k in ("model",)+BASELINES)
            if not present:
                reasons.append("Model and all three same-pixel baselines must be reported")
            else:
                model=metrics["model"]
                summary["spatial_holdout_metrics"]={k:{
                    "brier":metrics[k].get("brier"),
                    "f1":metrics[k].get("f1"),
                    "precision":metrics[k].get("precision"),
                    "recall":metrics[k].get("recall"),
                    "wet_truth_pixels":metrics[k].get("wet_truth_pixels"),
                    "evaluated_pixels":metrics[k].get("evaluated_pixels")}
                    for k in ("model",)+BASELINES}
                require(model.get("status")=="OK","Held-out metrics lack both wet and dry truth classes")
                require(_finite_number(model.get("wet_truth_pixels")) and model["wet_truth_pixels"]>=25,
                        "Too few wet pixels in held-out spatial test (minimum 25)")
                require(_finite_number(model.get("wet_prevalence")) and
                        model["wet_prevalence"]>=.01,
                        "Held-out wet prevalence below 1%; aggregate accuracy misleading")
                valid_brier=all(_finite_number(metrics[k].get("brier")) for k in ("model",)+BASELINES)
                valid_f1=all(_finite_number(metrics[k].get("f1")) for k in ("model",)+BASELINES)
                require(valid_brier and valid_f1,"Undefined test Brier or F1; no positive model claim")
                same_pixels=all(metrics[k].get("evaluated_pixels")==model.get("evaluated_pixels")
                                for k in BASELINES)
                require(same_pixels,"Baselines not evaluated on identical clear target pixels")
                if valid_brier and valid_f1:
                    best_baseline_brier=min(metrics[k]["brier"] for k in BASELINES)
                    best_baseline_f1=max(metrics[k]["f1"] for k in BASELINES)
                    improvement=best_baseline_brier-model["brier"]
                    summary["brier_improvement_over_best_baseline"]=improvement
                    summary["wet_f1_improvement_over_best_baseline"]=model["f1"]-best_baseline_f1
                    require(improvement>=.0005 and
                            improvement>=.02*best_baseline_brier,
                            "Spatial test Brier failed the 2% relative AND 0.0005 absolute gain")
                    require(model["f1"]>=best_baseline_f1+.02,
                            "Spatial test wet-class F1 did not improve by 0.02")
                require(_finite_number(spatial.get("shared_observed_fraction")) and
                        spatial["shared_observed_fraction"]>=.20,
                        "Too few shared clear pixels for a persuasive spatial test")
                months=spatial.get("monthly_paired_scores") or []
                if isinstance(months,list):
                    usable=[x for x in months if isinstance(x,dict) and x.get("status")=="OK"]
                    wet_months=sum(x.get("wet_pixels",0)>0 for x in usable)
                    require(len(usable)>=6 and wet_months>=3,
                            "Need at least six comparable months including three wet months")
                    comparable=[x for x in usable if _finite_number(x.get("candidate_minus_best_baseline"))]
                    if comparable:
                        improved=sum(x["candidate_minus_best_baseline"]<0 for x in comparable)
                        summary["improved_months"]=improved
                        summary["comparable_months"]=len(comparable)
                        require(improved>len(comparable)//2,
                                "Candidate did not beat monthly baseline in most comparable months")
                    else:reasons.append("Missing paired monthly losses")
                else:reasons.append("Monthly comparison is malformed")
    if not summary["independent_field_labels"]:
        reasons.append("No independently annotated or surveyed water labels: external ecological reliability unknown")
    summary["satellite_proxy_performance_passes"]=not any(
       r for r in reasons if not r.startswith("No independently annotated"))
    summary["status"]=("PROMISING_PROXY_EXPERIMENT_NOT_FIELD_VALIDATED"
                       if summary["satellite_proxy_performance_passes"] else "NOT_DEMONSTRATED")
    return summary

def markdown(result):
    s=["# Mash Plus V3 — independent judge-readiness audit",
       "",f"**Verdict:** {result['status']}",
       "**Field/operational certification:** NOT ESTABLISHED",
       "**Labels:** satellite MNDWI/NDVI proxy, not ground truth",
       ""]
    metrics=result.get("spatial_holdout_metrics",{})
    if metrics:
        s+=["| Spatial-holdout method | Brier ↓ | Wet F1 ↑ | Wet recall ↑ | Clear pixels |",
            "|---|---:|---:|---:|---:|"]
        for method,vals in metrics.items():
            def fmt(x):return f"{x:.5f}" if _finite_number(x) else "undefined"
            s.append(f"| {method} | {fmt(vals['brier'])} | {fmt(vals['f1'])} | "
                     f"{fmt(vals['recall'])} | {vals['evaluated_pixels']} |")
        s.append("")
    s.append("## Failure/limitation conditions")
    s.extend("- "+str(reason) for reason in result["reasons"])
    s+=["","The spatial holdout is new geography but its water labels are produced by the same",
        "satellite-index rule. Independent high-resolution or field reference data are essential.",
        "Per-pixel counts are correlated, not independent samples. This report is not a",
        "statistical confidence interval, peer review, or regulatory/scientific certification."]
    return "\n".join(s)+"\n"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--markdown",type=Path)
    args=p.parse_args()
    report=json.loads(args.input.read_text(encoding="utf8"))
    result=audit(report)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True,exist_ok=True)
        args.markdown.write_text(markdown(result),encoding="utf8")
    print(json.dumps({"status":result["status"],"reasons":result["reasons"]},
                     ensure_ascii=False))
if __name__=="__main__":main()
