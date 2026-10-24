"""Blinded TWO-REVIEWER reference evaluation (never synthesize a human label).

Requires dated independent high-resolution imagery or field evidence, two
different reviewers, identical sample IDs, and an original blind queue.
Outputs sample-conditional scores ONLY, never unbiased wetland area estimates
from the deliberately stratified reference sample.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,json,hashlib,math
from pathlib import Path
import numpy as np
from quality_gate import binary_metrics

LABEL_COLUMN="human_open_water_0_or_1_or_uncertain"
def read_csv(path):
    with open(path,newline="",encoding="utf8-sig") as file:
        values=list(csv.DictReader(file))
    if not values:raise ValueError("Empty annotation file "+str(path))
    ids=[str(row.get("sample_id","")).strip() for row in values]
    if not all(ids) or len(set(ids))!=len(ids):
        raise ValueError("Sample IDs absent or repeated in "+str(path))
    return {sid:row for sid,row in zip(ids,values)}
def paired_human_review(queue_path,review_a_path,review_b_path):
    queue=read_csv(queue_path)
    a=read_csv(review_a_path)
    b=read_csv(review_b_path)
    if not set(a)==set(b)==set(queue):
        raise ValueError("Two independent reviewers must annotate EXACTLY the original blind IDs")
    agreed={};conflicting=[];uncertain=[]
    who=set()
    for sid,row in queue.items():
        l=a[sid];r=b[sid]
        ua=str(l.get("reviewer_id","")).strip()
        ub=str(r.get("reviewer_id","")).strip()
        if not ua or not ub or ua==ub:
            raise ValueError("Two separate reviewer IDs required for "+sid)
        who.update((ua,ub))
        if len(who)>2:
            raise ValueError("Exactly two reviewer IDs per review batch")
        for ann in (l,r):
            if not str(ann.get("reference_image_source","")).strip():
                raise ValueError("Unverifiable reference imagery source at "+sid)
            when=dt.date.fromisoformat(str(ann.get("reference_image_date","")).strip())
            target=dt.date.fromisoformat(str(row["month"])+"-15")
            if abs((when-target).days)>45:
                raise ValueError("Reference imagery date too far from satellite target at "+sid)
            if ann.get(LABEL_COLUMN) not in ("0","1","uncertain"):
                raise ValueError("Reference label missing/invalid at "+sid)
        left=l[LABEL_COLUMN];right=r[LABEL_COLUMN]
        if "uncertain" in (left,right):
            uncertain.append(sid)
        elif left!=right:
            conflicting.append(sid)
        else:
            agreed[sid]=int(left)
    count=len(queue)
    return {"original_samples":count,"reviewer_ids":sorted(who),
            "two_reviewers_independent_by_identity_only":True,
            "agreement_count":len(agreed),"agreement_fraction":len(agreed)/count,
            "disagreements":conflicting,"uncertain":uncertain,
            "agreed_labels":agreed,
            "reference_type":"INDEPENDENT_HUMAN_IMAGE_INTERPRETATION_NOT_IN_SITU_FIELD_SURVEY",
            "estimated_area_accuracy_allowed":False}

def evaluate_on_forecasts(agreement,queue_path,manifest_path,predictions_path):
    queue=read_csv(queue_path)
    import rasterio
    from rasterio.transform import rowcol
    from rasterio.warp import transform
    from collect_sentinel import grid_for
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf8"))
    bbox=manifest["bbox_lonlat"]
    with np.load(predictions_path,allow_pickle=False) as z:
        dates=list(map(str,z["dates"].tolist()))
        model=np.asarray(z["model_probability"],dtype=np.float32)
        baseline=np.asarray(z["smoothed_persistence_probability"],dtype=np.float32)
        prev_observed=np.asarray(z["previous_observed"],dtype=bool)
    if model.shape!=baseline.shape or model.shape!=prev_observed.shape:
        raise ValueError("Model and baseline must use identical forecast grid")
    if model.ndim!=3 or model.shape[1]!=model.shape[2]:
        raise ValueError("Only study-grid forecasts supported")
    grid=grid_for(bbox,model.shape[1])
    indices={date:i for i,date in enumerate(dates)}
    p=[];q=[];y=[];matched_ids=[];months=set()
    for sid,reference in agreement["agreed_labels"].items():
        sample=queue[sid]
        t=indices.get(str(sample["month"]))
        if t is None:continue
        latitude=float(sample["latitude"])
        longitude=float(sample["longitude"])
        east,north=transform("EPSG:4326",grid["crs"],[longitude],[latitude])
        r,c=rowcol(grid["transform"],east[0],north[0])
        if not (0<=r<model.shape[1] and 0<=c<model.shape[2]):continue
        if not prev_observed[t,r,c]:continue
        p.append(float(model[t,r,c]));q.append(float(baseline[t,r,c]))
        y.append(reference);matched_ids.append(sid);months.add(dates[t])
    counts={"available_agreed":len(agreement["agreed_labels"]),
            "aligned_clear_target_samples":len(y),
            "wet_sample_labels":sum(y),"months":len(months)}
    if len(y)<50 or sum(y)<10 or len(months)<6:
        return {"status":"INCONCLUSIVE_INDEPENDENT_IMAGE_REFERENCE_SUPPORT",
                "counts":counts,"two_reviewers":agreement["reviewer_ids"],
                "disagreements":len(agreement["disagreements"]),
                "uncertain":len(agreement["uncertain"]),
                "field_validated":False}
    actual=np.asarray(y,dtype=np.float32)
    mask=np.ones(len(y),bool)
    scores={"neural":binary_metrics(np.asarray(p),actual,mask),
            "smoothed_persistence":binary_metrics(np.asarray(q),actual,mask)}
    return {"status":"UNWEIGHTED_STRATIFIED_IMAGE_REFERENCE_SCORES",
            "counts":counts,"two_reviewers":agreement["reviewer_ids"],
            "agreement_fraction":agreement["agreement_fraction"],
            "disagreements":len(agreement["disagreements"]),
            "uncertain":len(agreement["uncertain"]),
            "sample_conditional_scores":scores,
            "neural_brier_gain":scores["smoothed_persistence"]["brier"]-scores["neural"]["brier"],
            "population_accuracy_or_area_not_estimable":True,
            "in_situ_field_validated":False,
            "warning":"These two human interpreters of higher-resolution images are not ground-truth flow measurements; sample strata are intentionally oversampled and require design inclusion probabilities to estimate whole-marsh area accuracy."}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--queue",type=Path,required=True)
    p.add_argument("--review-a",type=Path,required=True)
    p.add_argument("--review-b",type=Path,required=True)
    p.add_argument("--spatial-manifest",type=Path,required=True)
    p.add_argument("--predictions",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    pair=paired_human_review(args.queue,args.review_a,args.review_b)
    result=evaluate_on_forecasts(pair,args.queue,args.spatial_manifest,args.predictions)
    result["source_hashes"]={
        k:hashlib.sha256(path.read_bytes()).hexdigest()
        for k,path in (("queue",args.queue),("review_a",args.review_a),
                       ("review_b",args.review_b),("predictions",args.predictions))}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
    print("INDEPENDENT_REFERENCE_AUDIT",result["status"])
if __name__=="__main__":main()
