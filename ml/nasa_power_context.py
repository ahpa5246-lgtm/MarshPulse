"""NASA POWER daily historical weather: free exogenous context (NOT yet ML input).

Daily point API: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
NASA data are coarse MERRA-2/reanalysis derived estimates and *not* a gauge
of Iraqi upstream river management. Missing days/months fail closed.
Every forecasting feature is computed strictly from months BEFORE target.
"""
from __future__ import annotations
from collections import defaultdict
import datetime as dt,hashlib,json,math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

URL="https://power.larc.nasa.gov/api/temporal/daily/point"
FEATURES=("PRECTOTCORR","T2M")
def request_url(latitude,longitude,start,end):
    if not (-90<=latitude<=90 and -180<=longitude<=180):
        raise ValueError("Invalid NASA POWER location")
    if not isinstance(start,dt.date) or not isinstance(end,dt.date) or start>end:
        raise ValueError("Invalid daily request window")
    params={"parameters":",".join(FEATURES),"community":"AG",
            "longitude":f"{longitude:.5f}","latitude":f"{latitude:.5f}",
            "start":start.strftime("%Y%m%d"),"end":end.strftime("%Y%m%d"),
            "format":"JSON"}
    return URL+"?"+urlencode(params)
def parse_daily_power(payload):
    params=payload.get("properties",{}).get("parameter",{})
    if not all(k in params and isinstance(params[k],dict) for k in FEATURES):
        raise ValueError("NASA POWER payload missing required daily variables")
    days=set(params["PRECTOTCORR"])&set(params["T2M"])
    monthly=defaultdict(list)
    for key in sorted(days):
        try:date=dt.datetime.strptime(key,"%Y%m%d").date()
        except ValueError:continue
        values=[params[p][key] for p in FEATURES]
        if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>-900 for v in values):
            continue
        rain,temp=map(float,values)
        if rain<0:continue
        monthly[date.strftime("%Y-%m")].append((date,rain,temp))
    out={}
    for month,rows in sorted(monthly.items()):
        year,m=map(int,month.split("-"))
        days_in_month=((dt.date(year+1,1,1) if m==12 else dt.date(year,m+1,1))-
                       dt.date(year,m,1)).days
        seen={date for date,*_ in rows}
        # An incomplete month is missing, not zero rainfall.
        if len(seen)!=days_in_month:continue
        out[month]={"rainfall_mm_month":sum(row[1] for row in rows),
                    "temperature_c_mean":sum(row[2] for row in rows)/days_in_month,
                    "days":len(seen)}
    return out
def past_only_features(months,target):
    """Causal 1-month/3-month weather known at forecast origin."""
    d=dt.date.fromisoformat(target+"-01")
    previous=[]
    for k in range(1,4):
        y=(d.year*12+d.month-1-k)//12
        m=(d.year*12+d.month-1-k)%12+1
        month=f"{y:04d}-{m:02d}"
        if month not in months:return None
        previous.append(months[month])
    return {"target_month":target,"source_last_month":f"{(d.replace(day=1)-dt.timedelta(days=1)).year:04d}-{(d.replace(day=1)-dt.timedelta(days=1)).month:02d}",
            "rainfall_previous_month_mm":previous[0]["rainfall_mm_month"],
            "rainfall_last_3months_mm":sum(x["rainfall_mm_month"] for x in previous),
            "temperature_previous_month_c":previous[0]["temperature_c_mean"]}
def fetch_context(bbox,start,end,timeout=40):
    if not (isinstance(bbox,list) and len(bbox)==4):
        raise ValueError("Expected four-element AOI bounding rectangle")
    lat=(bbox[1]+bbox[3])/2
    lon=(bbox[0]+bbox[2])/2
    # Include three preceding months, without any lookahead.
    initial=dt.date.fromisoformat(start+"-01")
    start_prev=dt.date(initial.year-1,initial.month,1)
    stop=dt.date.fromisoformat(end+"-01")
    stop=stop-dt.timedelta(days=1)  # Only complete months before last target.
    url=request_url(lat,lon,start_prev,stop)
    req=Request(url,headers={"User-Agent":"MashPlus-Research/1.0","Accept":"application/json"})
    with urlopen(req,timeout=timeout) as response:raw=response.read()
    if len(raw)>12_000_000:raise ValueError("Unexpectedly oversized NASA response")
    parsed=json.loads(raw)
    monthly=parse_daily_power(parsed)
    if len(monthly)<6:raise ValueError("Insufficient NASA POWER complete months")
    targets=[]
    current=dt.date.fromisoformat(start+"-01")
    until=dt.date.fromisoformat(end+"-01")
    while current<=until:
        targets.append(current.strftime("%Y-%m"))
        current=(current.replace(day=28)+dt.timedelta(days=4)).replace(day=1)
    return {"source":"NASA POWER Daily AG, historical MERRA-2/reanalysis-derived meteorology",
            "api_url":url,"retrieved_bytes_sha256":hashlib.sha256(raw).hexdigest(),
            "location":{"latitude":lat,"longitude":lon},
            "contains_predictive_training_integration":False,
            "not_river_discharge_or_field_truth":True,
            "complete_month_count":len(monthly),
            "monthly":monthly,
            "forecast_context_by_month":{month:past_only_features(monthly,month)
                for month in targets if past_only_features(monthly,month) is not None}}
def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    source=json.loads(args.manifest.read_text())
    out=fetch_context(source["bbox_lonlat"],args.start,args.end)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print("NASA_POWER_MONTHS",out["complete_month_count"],
          "rainfall usable as past-only CONTEXT, not ML input until independent ablation")
if __name__=="__main__":main()
