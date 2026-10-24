#!/usr/bin/env python3
"""Prepare a blinded, georeferenced human-reference review queue from REAL scenes.

Sampling strata come from satellite proxy only to ensure class coverage.
This is NOT a field-labeled dataset: human_ref fields are intentionally blank.
Annotators must inspect temporally matched independent/high-resolution imagery.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
import numpy as np
from quality_gate import wet_proxy
from collect_sentinel import grid_for

def neighborhood(water):
    """Four-neighbor boundary from numpy only (no invented images)."""
    padded=np.pad(np.asarray(water,dtype=bool),1,constant_values=False)
    h,w=water.shape
    n=padded[:h,1:w+1]|padded[2:h+2,1:w+1]
    n|=padded[1:h+1,:w]|padded[1:h+1,2:w+2]
    return n & ~water

def stratified_cells(x,dates,per_month=9,seed=20261024):
    if x.ndim!=4 or x.shape[1]!=7 or len(dates)!=len(x):
        raise ValueError("Expected real monthly 7-band Sentinel cube")
    if not 3<=per_month<=300:raise ValueError("Per-month sample count out of range")
    water,observed=wet_proxy(x)
    rng=np.random.default_rng(seed)
    result=[]
    strata={"wet":0,"shoreline":0,"dry":0}
    for t,date in enumerate(dates):
        wet=water[t];good=observed[t]
        # The shoreline is a PROXY buffer around observed wet pixels.
        edge=neighborhood(wet)&good
        pools={"wet":np.argwhere(wet&good),
               "shoreline":np.argwhere(edge),
               "dry":np.argwhere(good&~wet&~edge)}
        quota={"wet":per_month//3,
               "shoreline":per_month//3,
               "dry":per_month-2*(per_month//3)}
        used=set()
        for stratum in ("wet","shoreline","dry"):
            pool=pools[stratum]
            if len(pool)==0:continue
            selections=rng.choice(len(pool),size=min(len(pool),quota[stratum]),replace=False)
            for index in np.atleast_1d(selections):
                row,col=map(int,pool[index])
                if (row,col) in used:continue
                used.add((row,col));strata[stratum]+=1
                result.append({"month":str(date),"row":row,"col":col,
                               "stratum":stratum,"observed":True})
    return result,strata

def write_queue(cube,manifest,output,per_month=9,seed=20261024,last_months=12):
    cube=Path(cube);manifest=Path(manifest);output=Path(output)
    obj=json.loads(manifest.read_text(encoding="utf8"))
    if not obj.get("source","").startswith("REAL ESA Sentinel-2"):
        raise ValueError("Only real scene manifests may support human-review tasks")
    with np.load(cube,allow_pickle=False) as z:
        x=np.asarray(z["x"],dtype=np.float32)
        dates=z["dates"].astype(str)
    if len(obj.get("months",[]))!=len(x):raise ValueError("Scene manifest incomplete")
    if last_months<3 or last_months>len(x):raise ValueError("Invalid review period")
    x=x[-last_months:];dates=dates[-last_months:]
    samples,counts=stratified_cells(x,dates,per_month=per_month,seed=seed)
    if not samples:raise ValueError("No real observed pixels for review")
    grid=grid_for(obj["bbox_lonlat"],x.shape[-1])
    from rasterio.transform import xy
    from rasterio.warp import transform
    output.mkdir(parents=True,exist_ok=True)
    queue=output/"blinded_human_reference_queue.csv"
    with queue.open("w",newline="",encoding="utf8") as f:
        writer=csv.DictWriter(f,fieldnames=["sample_id","month","latitude","longitude",
                        "reference_image_source","reference_image_date",
                        "human_open_water_0_or_1_or_uncertain","reviewer_id",
                        "independent_reviewer_id","remarks"])
        writer.writeheader()
        for i,item in enumerate(samples):
            e,n=xy(grid["transform"],item["row"],item["col"])
            lon,lat=transform(grid["crs"],"EPSG:4326",[e],[n])
            writer.writerow({"sample_id":f"MP-{i+1:04d}","month":item["month"],
                         "latitude":f"{lat[0]:.6f}","longitude":f"{lon[0]:.6f}"})
    audit={"status":"UNLABELED_HUMAN_REVIEW_TASKS_ONLY",
           "water_truth_independently_validated":False,
           "method":"stratified months, wet-proxy/shoreline/dry candidate sampling",
           "sampling_source":"unverified Sentinel MNDWI/NDVI proxy for stratification",
           "source_manifest_sha256":hashlib.sha256(manifest.read_bytes()).hexdigest(),
           "source_data_sha256":hashlib.sha256(cube.read_bytes()).hexdigest(),
           "seed":seed,"per_month_target":per_month,"months":list(map(str,dates)),
           "samples":len(samples),"source_strata":counts,
           "sample_id_to_proxy_stratum":[{"sample_id":f"MP-{i+1:04d}",
                                          "proxy_stratum":s["stratum"]}
                                         for i,s in enumerate(samples)],
           "instructions":"Two independent people annotate from dated high-res imagery or field evidence; uncertain is allowed. Never label from Mash Plus prediction or reuse its MNDWI target as independent truth. Stratified estimates require sampling weights."}
    (output/"private_sampling_audit_DO_NOT_SHOW_ANNOTATORS.json").write_text(json.dumps(audit,indent=2),encoding="utf8")
    print("HUMAN_REVIEW_QUEUE",len(samples),"UNLABELED",queue)
    return audit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cube",required=True,type=Path)
    p.add_argument("--manifest",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--per-month",type=int,default=9)
    p.add_argument("--last-months",type=int,default=12)
    args=p.parse_args()
    write_queue(args.cube,args.manifest,args.out,args.per_month,last_months=args.last_months)
if __name__=="__main__":
    main()
