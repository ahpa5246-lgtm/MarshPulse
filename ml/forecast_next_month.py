"""Actual next-calendar-month Marsh Plus inference, using PAST images only.

This never reads the future satellite target; the last available observation
is the forecast origin. Spatial grid cells are COARSE and must not be sold as
10m Sentinel-2-resolution hydrologic predictions. Research-only proxy.
"""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np
import torch
from marshnet_v3 import MarshNetV3
from train_v3 import load_region,stats,next_month

TRAIN_NAMES=("hawizeh_train","central_train","sinnaf_train")
def forward_forecast(model,past,mean,std,device="cpu"):
    past=np.asarray(past,dtype=np.float32)
    if past.ndim!=4 or past.shape[1]!=7 or past.shape[0]<2:
        raise ValueError("Need historical [T,7,H,W] before unknown target")
    if len(mean)!=6 or len(std)!=6 or not np.all(np.asarray(std)>0):
        raise ValueError("Training-only normalization unavailable")
    history=past.copy()
    for c in range(6):
        history[:,c]=np.where(past[:,6]>.5,
                              (past[:,c]-mean[c])/std[c],0.)
    observed=past[-1,6]>.5
    wet=(past[-1,5]>.1)&(past[-1,4]<.3)
    prior=np.where(observed,np.where(wet,.99,.01),.5).astype(np.float32)
    model=model.to(device)
    model.eval()
    with torch.inference_mode():
        logits=model(torch.from_numpy(history[None].copy()).to(device),
                     torch.from_numpy(prior[None].copy()).to(device))
        p=logits.sigmoid()[0].float().cpu().numpy()
    if not np.isfinite(p).all() or (p<0).any() or (p>1).any():
        raise RuntimeError("Invalid wet-proxy forecast")
    return p.astype(np.float32),prior

def run(state_file,data_root,out,device="cpu",synthetic_smoke=False):
    state=torch.load(state_file,map_location="cpu",weights_only=True)
    if state.get("protocol")!="mash-plus-daily-v1" or state.get("field_validated") is not False:
        raise ValueError("Missing research-only daily model state")
    args=state["architecture"]
    paths=[Path(data_root)/"source_imagery"/name/"hawizeh_s2_monthly.npz"
           for name in TRAIN_NAMES]
    regions=[load_region(p,synthetic=synthetic_smoke) for p in paths]
    if state.get("train_data_sha256")!=[r["sha"] for r in regions]:
        raise ValueError("Inference source normalization data differ from saved state")
    mean,std=stats(regions,args["lookback"])
    model=MarshNetV3(base=args["base"])
    model.load_state_dict(state["best_weights"])
    output=Path(out);output.mkdir(parents=True,exist_ok=True)
    summaries={}
    for name,region in zip(TRAIN_NAMES,regions):
        origin=region["dates"][-1]
        target=next_month(origin)
        forecast,persistence=forward_forecast(model,
                           region["x"][-args["lookback"]:],mean,std,device=device)
        filename=output/f"{name}_forecast_{target}.npz"
        np.savez_compressed(filename,model_wet_proxy_probability=forecast,
                 persistence_wet_proxy_probability=persistence,
                 training_scene_sha256=np.asarray(region["sha"]),
                 previous_observed_date=np.asarray(origin),
                 future_forecast_month=np.asarray(target))
        summaries[name]={"origin_month":origin,"forecast_month":target,
            "image_grid_shape":list(forecast.shape),
            "area_wet_probability_mean":float(forecast.mean()),
            "baseline_wet_probability_mean":float(persistence.mean()),
            "model_vs_persistence_mae":float(np.abs(forecast-persistence).mean()),
            "file":filename.name,
            "checksum_sha256":hashlib.sha256(filename.read_bytes()).hexdigest()}
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig,ax=plt.subplots(figsize=(6,5))
            im=ax.imshow(forecast,vmin=0,vmax=1,cmap="Blues")
            ax.set_title(f"Mash Plus | {name} | {target}\nCOARSE satellite wet-proxy forecast")
            ax.set_xlabel("grid columns");ax.set_ylabel("grid rows")
            fig.colorbar(im,ax=ax,label="wet proxy probability (research only)")
            fig.savefig(output/f"{name}_forecast_{target}.png",dpi=150,bbox_inches="tight")
            plt.close(fig)
        except ImportError:pass
    summary={"model":"Mash Plus ConvGRU daily best validation checkpoint",
        "status":"UNVERIFIED_FUTURE_PROXY_FORECAST",
        "source_only_prior_images":True,"future_target_labels_used":False,
        "field_or_water_volume_prediction":False,
        "normalize_using_training_regions_only":True,
        "note":"These are per-cell wet-proxy probability forecasts on a coarse study grid, not field-verified water areas or real-time 10m maps.",
        "forecasts":summaries}
    (output/"forecast_provenance.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n")
    return summary

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--state",type=Path,required=True)
    p.add_argument("--data",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cpu",action="store_true")
    args=p.parse_args()
    result=run(args.state,args.data,args.out,device="cpu" if args.cpu or not torch.cuda.is_available() else "cuda")
    print("FORECAST_MAP_CREATED",json.dumps({k:v["forecast_month"] for k,v in result["forecasts"].items()}))
if __name__=="__main__":main()
