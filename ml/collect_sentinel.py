#!/usr/bin/env python3
"""Real Sentinel-2 acquisition through Planetary Computer for a HAWIZEH pilot box.
Requires Kaggle Internet. Never substitutes generated imagery or fake labels.
"""
import argparse,json
from collections import defaultdict
from pathlib import Path
import numpy as np
BANDS=("B03","B04","B08","B11")
FEATURES=("B03","B04","B08","B11","NDVI","MNDWI","VALID")
def next_month(x):
    y,m=map(int,x.split("-"));return f"{y+(m==12):04d}-{m%12+1:02d}"
def keys(start,end):
    """Inclusive, bounded monthly range. Invalid input must never loop forever."""
    import re
    for date in (start,end):
        if not re.fullmatch(r"\\d{4}-(0[1-9]|1[0-2])",date):
            raise ValueError("Dates must be YYYY-MM with month 01–12")
    if start>end:
        raise ValueError("Start month must precede end month")
    m=[start]
    while m[-1]!=end:
        if len(m)>=240:raise ValueError("Date window exceeds 240 months")
        m.append(next_month(m[-1]))
    return m
def grid_for(bbox,pixels):
    from rasterio.transform import from_origin
    from rasterio.warp import transform_bounds
    zone=int(((bbox[0]+bbox[2])/2+180)//6)+1
    epsg=f"EPSG:{32600+zone}"
    west,south,east,north=transform_bounds("EPSG:4326",epsg,*bbox)
    resolution=max((east-west)/pixels,(north-south)/pixels)
    x=(west+east-pixels*resolution)/2;y=(south+north+pixels*resolution)/2
    return dict(crs=epsg,width=pixels,height=pixels,resolution_m=resolution,transform=from_origin(x,y,resolution,resolution))
def query(bbox,start,end,cloud):
    from pystac_client import Client
    import planetary_computer
    catalog=Client.open("https://planetarycomputer.microsoft.com/api/stac/v1",modifier=planetary_computer.sign_inplace)
    search=catalog.search(collections=["sentinel-2-l2a"],bbox=bbox,
                          datetime=start+"-01/"+next_month(end)+"-01",
                          query={"eo:cloud_cover":{"lt":cloud}},max_items=1200)
    months=defaultdict(list)
    for item in search.items():months[item.datetime.strftime("%Y-%m")].append(item)
    for m in months:months[m].sort(key=lambda it:(float(it.properties.get("eo:cloud_cover",100)),abs(it.datetime.day-15)))
    return months
def band(item,key,grid,nearest=False):
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.enums import Resampling
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",GDAL_HTTP_MAX_RETRY="3"):
        with rasterio.open(item.assets[key].href) as src:
            with WarpedVRT(src,crs=grid["crs"],transform=grid["transform"],
                           width=grid["width"],height=grid["height"],
                           resampling=Resampling.nearest if nearest else Resampling.bilinear) as vrt:
                return vrt.read(1,masked=True).filled(0).astype(np.float32)
def scene(item,grid):
    arrays=[band(item,key,grid) for key in BANDS]
    scl=band(item,"SCL",grid,nearest=True).astype(np.int16)
    valid=np.isin(scl,[4,5,6])&np.logical_and.reduce([a>0 for a in arrays])
    return np.stack([np.clip(a/10000.,0,1) for a in arrays]).astype(np.float32),valid
def monthly(items,grid,n):
    sum_=np.zeros((4,grid["height"],grid["width"]),np.float32)
    count=np.zeros((grid["height"],grid["width"]),np.float32)
    used=[];failures=[]
    for item in items[:n]:
        try:values,valid=scene(item,grid)
        except Exception as e:failures.append({"item":item.id,"error_type":type(e).__name__});continue
        sum_+=values*valid[None];count+=valid
        used.append({"item":item.id,"acquired":item.datetime.isoformat(),"cloud_cover":item.properties.get("eo:cloud_cover")})
    out=np.zeros((7,grid["height"],grid["width"]),np.float32)
    good=count>0
    np.divide(sum_,count[None],out=out[:4],where=good[None])
    g,r,nir,swir=out[:4]
    out[4]=np.divide(nir-r,nir+r+1e-6,out=np.zeros_like(g),where=good)
    out[5]=np.divide(g-swir,g+swir+1e-6,out=np.zeros_like(g),where=good)
    out[6]=good.astype(np.float32)
    return out,used,failures
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bbox",nargs=4,type=float,default=[47.55,31.50,47.65,31.60])
    p.add_argument("--start",default="2023-01");p.add_argument("--end",default="2025-12")
    p.add_argument("--pixels",type=int,default=96);p.add_argument("--max-scenes",type=int,default=2)
    p.add_argument("--cloud",type=float,default=80);p.add_argument("--min-coverage",type=float,default=.2)
    p.add_argument("--out",type=Path,default=Path("/kaggle/working/marshpulse/sentinel"))
    args=p.parse_args()
    if args.pixels%4 or not 32<=args.pixels<=256:raise ValueError("pixels must be divisible by 4 in [32,256]")
    if not (args.bbox[0]<args.bbox[2] and args.bbox[1]<args.bbox[3]):raise ValueError("Invalid AOI bbox")
    months=keys(args.start,args.end)
    if len(months)<24:raise ValueError("At least 24 months required")
    grid=grid_for(args.bbox,args.pixels)
    found=query(args.bbox,args.start,args.end,args.cloud)
    images=[];records=[];errors=[]
    for month in months:
        im,scenes,fail=monthly(found.get(month,[]),grid,args.max_scenes)
        frac=float(im[6].mean())
        print(month,"observed",f"{frac:.1%}","scenes",len(scenes),flush=True)
        images.append(im);records.append({"month":month,"fraction_valid":frac,"scenes":scenes});errors+=fail
    good=sum(r["fraction_valid"]>=args.min_coverage for r in records)
    if good<max(12,int(len(months)*.55)):
        raise RuntimeError(f"Insufficient clear-image coverage: {good}/{len(months)} months. NO fabricated data saved.")
    args.out.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(args.out/"hawizeh_s2_monthly.npz",x=np.stack(images),dates=np.asarray(months),bands=np.asarray(FEATURES))
    provenance={"source":"REAL ESA Sentinel-2 L2A via Microsoft Planetary Computer",
                "location":"Hawizeh approximate pilot rectangle, NOT official Ramsar boundary",
                "bbox_lonlat":args.bbox,"epsg":grid["crs"],"pixel_size_m":grid["resolution_m"],
                "months":records,"errors":errors,"bands":FEATURES,
                "labels":"UNVERIFIED water proxies from threshold MNDWI>0.1 & NDVI<0.3",
                "field_ground_truth":False,"missing_data":"VALID=0; never relabeled as dry",
                "license":"Copernicus Sentinel Data Terms and Conditions"}
    (args.out/"satellite_manifest.json").write_text(json.dumps(provenance,indent=2,ensure_ascii=False))
    print("Saved genuine imagery:",args.out/"hawizeh_s2_monthly.npz")
if __name__=="__main__":main()
