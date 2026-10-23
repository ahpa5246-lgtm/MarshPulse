#!/usr/bin/env python3
"""Actual observed-pixel wetland monitoring from acquired Sentinel-2 scenes.

This is a transparent MNDWI/NDVI screening product, NOT ground-truth water,
hydraulic connectivity, ecological restoration outcome, or area extrapolation.
"""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import numpy as np
from quality_gate import wet_proxy,FEATURE_NAMES

def components8(mask):
    """Count disconnected 8-neighbor clusters of proxy-wet OBSERVED pixels."""
    a=np.asarray(mask,dtype=bool)
    if a.ndim!=2:raise ValueError("Expected a 2D map")
    visited=np.zeros_like(a)
    regions=[]
    height,width=a.shape
    for y,x in zip(*np.nonzero(a)):
        if visited[y,x]:continue
        visited[y,x]=True;stack=[(int(y),int(x))];size=0
        while stack:
            row,col=stack.pop();size+=1
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    nr,nc=row+dy,col+dx
                    if 0<=nr<height and 0<=nc<width and a[nr,nc] and not visited[nr,nc]:
                        visited[nr,nc]=True;stack.append((nr,nc))
        regions.append(size)
    return regions

def monitor(cube,dates,pixel_size_m,minimum_coverage=.20):
    x=np.asarray(cube)
    if not np.isfinite(pixel_size_m) or pixel_size_m<=0:
        raise ValueError("Pixel size must be a positive projected metre measurement")
    wet,valid=wet_proxy(x)
    if len(dates)!=len(x):raise ValueError("Data/date mismatch")
    pixel_km2=float(pixel_size_m)**2/1e6
    records=[]
    for i in range(len(x)):
        total=int(valid[i].size);observed=int(valid[i].sum())
        area=int(wet[i].sum())*pixel_km2
        coverage=observed/total
        fragments=components8(wet[i])
        item={"month":str(dates[i]),"observed_fraction":coverage,
              "observed_area_km2":observed*pixel_km2,
              "proxy_wet_observed_area_km2":area,
              "proxy_wet_fraction_of_observed":int(wet[i].sum())/observed if observed else None,
              "pixel_clusters_not_hydraulic_connections":len(fragments),
              "largest_wet_pixel_cluster_km2":max(fragments,default=0)*pixel_km2,
              "status":"SCREENING_ONLY" if coverage>=minimum_coverage else "LOW_OBSERVATION"}
        if i:
            common=valid[i]&valid[i-1]
            n=int(common.sum());item["month_to_month_common_observed_fraction"]=n/total
            if n/total<minimum_coverage:
                item["observed_wet_change_km2"]=None
                item["new_wet_km2"]=None;item["no_longer_wet_km2"]=None
                item["change_note"]="INSUFFICIENT_MATCHED_CLEAR_PIXELS"
            else:
                newly=wet[i]&~wet[i-1]&common
                vanished=wet[i-1]&~wet[i]&common
                item["new_wet_km2"]=int(newly.sum())*pixel_km2
                item["no_longer_wet_km2"]=int(vanished.sum())*pixel_km2
                item["observed_wet_change_km2"]=int(newly.sum()-vanished.sum())*pixel_km2
                item["change_note"]="MATCHED_OBSERVED_PIXELS_ONLY_NOT_AOI_TOTAL"
        else:
            item["month_to_month_common_observed_fraction"]=None
            item["observed_wet_change_km2"]=None
            item["new_wet_km2"]=None;item["no_longer_wet_km2"]=None
            item["change_note"]="NO_PREVIOUS_MONTH"
        records.append(item)
    return {
      "source":"REAL Sentinel-2 L2A, only if supplied with acquisition manifest",
      "target":"Water proxy MNDWI>0.1 AND NDVI<0.3 on masked clear observations",
      "ground_truth_verified":False,
      "hydraulic_connectivity_measured":False,
      "limitations":["Scene-classification and thresholds miss vegetated water",
                      "Only observed area counted; clouds and no-data NOT called dry",
                      "Pixel connectivity is not physical/hydraulic connectivity",
                      "Month-to-month changes use overlap of valid pixels ONLY",
                      "AOI is a pilot box, not an official wetland polygon"],
      "pixel_area_km2":pixel_km2,
      "monthly":records}

def main():
    pa=argparse.ArgumentParser()
    pa.add_argument("--input",type=Path,required=True)
    pa.add_argument("--manifest",type=Path,required=True)
    pa.add_argument("--out",type=Path,required=True)
    args=pa.parse_args()
    manifest=json.loads(args.manifest.read_text(encoding="utf8"))
    if not manifest.get("source","").startswith("REAL ESA Sentinel-2") or not any(
          month.get("scenes") for month in manifest.get("months",[])):
        raise ValueError("Missing real-satellite acquisition evidence")
    with np.load(args.input,allow_pickle=False) as archive:
        if archive["bands"].tolist()!=list(FEATURE_NAMES):
            raise ValueError("Band schema mismatch")
        report=monitor(archive["x"],archive["dates"].tolist(),manifest["pixel_size_m"])
    report["study_area_bbox_lonlat"]=manifest.get("bbox_lonlat")
    report["study_area_official_boundary"]=False
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"water_monitor.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    columns=list(report["monthly"][0]) if report["monthly"] else []
    with (args.out/"water_monitor.csv").open("w",encoding="utf8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(report["monthly"])
    print("ACTUAL OBSERVED MONTHLY MONITORING:",len(report["monthly"]),"months; proxy labels not verified")
if __name__=="__main__":main()
