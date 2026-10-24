#!/usr/bin/env python3
"""Independent-SENSOR satellite screening, not independent WATER TRUTH.

Compare sealed next-month Mash Plus predictions against Landsat 8/9 Collection 2
Level-2 imagery from Microsoft Planetary Computer, not Sentinel labels used for
training. Monthly acquisition timing, 30m->pilot-grid resampling, uncertain wet
thresholds, and similar optical sensor physics limit the interpretation.
No Landsat target can influence a checkpoint or a hyperparameter.
"""
from __future__ import annotations
import argparse,json,hashlib
from collections import defaultdict
from pathlib import Path
import numpy as np
from quality_gate import binary_metrics
from collect_sentinel import grid_for

ASSETS=("green","red","nir08","swir16")

def landsat_clear_qa(qa):
    """USGS QA_PIXEL bit layout: reject fill, clouds, shadows and snow.
    Do not use the QA water flag, because that would encode a different label.
    """
    q=np.asarray(qa,dtype=np.uint16)
    invalid_bits=(0,1,2,3,4,5)
    bad=np.zeros(q.shape,dtype=bool)
    for bit in invalid_bits:bad|=(q&(1<<bit))!=0
    return ~bad

def read_asset(item,asset,grid,nearest=False):
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.vrt import WarpedVRT
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",GDAL_HTTP_MAX_RETRY="3"):
        with rasterio.open(item.assets[asset].href) as src:
            with WarpedVRT(src,crs=grid["crs"],transform=grid["transform"],
                           width=grid["width"],height=grid["height"],
                           resampling=Resampling.nearest if nearest else Resampling.average) as vrt:
                return vrt.read(1,masked=True).filled(0).astype(np.float32)

def scene(item,grid):
    raw=np.stack([read_asset(item,key,grid) for key in ASSETS])
    qa=read_asset(item,"qa_pixel",grid,nearest=True).astype(np.uint16)
    # USGS Landsat C2 L2 surface reflectance scale and offset for SR bands.
    scaled=raw*0.0000275-0.2
    clear=landsat_clear_qa(qa)&np.isfinite(scaled).all(axis=0)&np.all(raw>0,axis=0)
    green,red,nir,swir=scaled
    ndvi=(nir-red)/(nir+red+1e-6)
    mndwi=(green-swir)/(green+swir+1e-6)
    good=clear&(np.abs(nir+red)>.02)&(np.abs(green+swir)>.02)
    return ((mndwi>.1)&(ndvi<.3)&good),good

def fetch_months(bbox,start,end,cloud=80):
    from pystac_client import Client
    import planetary_computer
    from collect_sentinel import next_month
    catalog=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",
                        modifier=planetary_computer.sign_inplace)
    iterator=catalog.search(collections=["landsat-c2-l2"],bbox=bbox,
                            datetime=start+"-01/"+next_month(end)+"-01",
                            query={"eo:cloud_cover":{"lt":cloud}},max_items=600).items()
    items=defaultdict(list)
    for it in iterator:
        # Landsat C2 L2 reflectance products may be missing on some acquisitions.
        if all(k in it.assets for k in (*ASSETS,"qa_pixel")):
            items[it.datetime.strftime("%Y-%m")].append(it)
    for month in items:
        items[month].sort(key=lambda i:(float(i.properties.get("eo:cloud_cover",100)),
                                         abs(i.datetime.day-15)))
    return items

def combined_month(items,grid,max_scenes=2):
    h,w=grid["height"],grid["width"]
    observed=np.zeros((h,w),bool)
    wet=np.zeros((h,w),bool)
    sources=[]
    for item in items[:max_scenes*6]:
        if len(sources)>=max_scenes:break
        try:water,clear=scene(item,grid)
        except Exception:continue
        if not clear.any():continue
        new=clear & ~observed
        wet[new]=water[new]
        observed|=clear
        sources.append({"scene_id":item.id,"acquired":item.datetime.isoformat()})
    return wet,observed,sources

def compare_arrays(probs,baseline,labels,clear,previous_observed,dates,min_months=6):
    prob=np.asarray(probs);base=np.asarray(baseline)
    truth=np.asarray(labels);valid=np.asarray(clear,dtype=bool)&np.asarray(previous_observed,dtype=bool)
    if prob.shape!=base.shape or prob.shape!=truth.shape or prob.shape!=valid.shape:
        raise ValueError("Matched grid/time shapes required")
    if len(dates)!=len(prob):raise ValueError("Date count mismatch")
    good_months=int(valid.reshape(len(valid),-1).any(axis=1).sum())
    model=binary_metrics(prob,truth,valid)
    persistence=binary_metrics(base,truth,valid)
    status="SCREENED_DIFFERENT_SENSOR_NOT_FIELD_TRUTH" if good_months>=min_months and model.get("wet_truth_pixels",0)>=25 else "INCONCLUSIVE_INSUFFICIENT_SUPPORT"
    return {"status":status,"source":"Landsat 8/9 C2 L2 independent sensor, derived water INDEX not manual labels",
            "temporally_exact_field_reference":False,"independent_field_labels":False,
            "months_compared":good_months,"wet_proxy_pixels":model.get("wet_truth_pixels",0),
            "matched_observed_pixels":model.get("evaluated_pixels",0),
            "model":model,"persistence":persistence,
            "reliability_certified":False}

def run(source,spatial_npz,out,max_months=12,max_scenes=2):
    manifest=json.loads(Path(source).read_text(encoding="utf8"))
    bbox=manifest.get("bbox_lonlat")
    if not isinstance(bbox,list) or len(bbox)!=4:
        raise ValueError("Invalid held-out spatial acquisition bounds")
    with np.load(spatial_npz,allow_pickle=False) as z:
        dates=list(map(str,z["dates"].tolist()))
        prob=np.asarray(z["model_probability"],dtype=np.float32)
        base=np.asarray(z["persistence_probability"],dtype=np.float32)
        past=np.asarray(z["previous_observed"],dtype=bool)
    if len(dates)<max_months:raise ValueError("Short held-out period")
    dates=dates[-max_months:]
    prob=prob[-max_months:];base=base[-max_months:];past=past[-max_months:]
    if prob.ndim!=3 or prob.shape[1]!=prob.shape[2]:
        raise ValueError("Need square spatial probability grids")
    grid=grid_for(bbox,prob.shape[1])
    acquired=fetch_months(bbox,dates[0],dates[-1])
    labels=[];valid=[];details=[]
    for date in dates:
        wet,good,scenes=combined_month(acquired.get(date,[]),grid,max_scenes=max_scenes)
        labels.append(wet);valid.append(good)
        details.append({"month":date,"source_scenes":scenes,
                        "observed_fraction":float(good.mean())})
        print("LANDSAT_REVIEW",date,"scenes",len(scenes),"clear",round(float(good.mean()),4),flush=True)
    result=compare_arrays(prob,base,np.stack(labels),np.stack(valid),past,dates)
    result["monthly_sources"]=details
    result["heldout_bbox"]=bbox
    result["prediction_sha256"]=hashlib.sha256(Path(spatial_npz).read_bytes()).hexdigest()
    result["landsat_collection"]="landsat-c2-l2"
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf8")
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--spatial-manifest",required=True,type=Path)
    p.add_argument("--predictions",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--months",type=int,default=12)
    args=p.parse_args()
    if not 6<=args.months<=36:raise ValueError("Cross-sensor review requires 6-36 months")
    r=run(args.spatial_manifest,args.predictions,args.out,max_months=args.months)
    print("CROSS_SENSOR_STATUS",r["status"],"wet_pixels",r["wet_proxy_pixels"],flush=True)
if __name__=="__main__":
    main()
