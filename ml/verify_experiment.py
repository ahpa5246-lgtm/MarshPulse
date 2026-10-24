#!/usr/bin/env python3
"""Independent artifact replay: verify source integrity, test-mask equality and benchmark scores.

PASS means internally reproducible satellite-proxy evidence, NOT scientifically
validated water forecasts or a reliable real-world restoration recommendation.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np

BANDS=("B03","B04","B08","B11","NDVI","MNDWI","VALID")

def verify(data_path,manifest_path,evaluation_path,predictions_path,monitor_path):
    data_path=Path(data_path)
    report=json.loads(Path(evaluation_path).read_text())
    manifest=json.loads(Path(manifest_path).read_text())
    monthly=json.loads(Path(monitor_path).read_text())
    digest=hashlib.sha256(data_path.read_bytes()).hexdigest()
    assert digest==report["dataset_sha256"],"Satellite dataset SHA-256 mismatch"
    with np.load(data_path,allow_pickle=False) as a:
        images=a["x"];dates=a["dates"].tolist()
        assert a["bands"].tolist()==list(BANDS),"Incorrect channel order"
    with np.load(predictions_path,allow_pickle=False) as z:
        probability=z["probabilities"];raw=z["raw_probabilities"]
        y_saved=z["targets"];mask_saved=z["observed"];p_dates=z["dates"].tolist()
    assert images.ndim==4 and images.shape[1]==7 and len(images)>=24
    assert np.isfinite(images).all() and np.isin(images[:,6],[0,1]).all()
    assert dates==report["dates"] and len(set(dates))==len(dates)
    assert [entry["month"] for entry in manifest["months"]]==dates
    assert all(entry["scenes"] for entry in manifest["months"]),"Month without genuine scenes"
    assert manifest["source"].startswith("REAL ESA Sentinel-2")
    splits=report["split_targets"]
    tr,va,te=(splits[k] for k in ("train","validation","test"))
    assert tr and va and te and max(tr)<min(va) and max(va)<min(te),"Date split leakage"
    assert all(i>=12 for i in te),"Missing seasonal baseline history"
    observed=images[:,6]>.5
    wet=(images[:,5]>.1)&(images[:,4]<.3)&observed
    assert len(te)==len(probability)==len(raw)==len(p_dates)
    assert probability.shape==raw.shape==y_saved.shape==mask_saved.shape
    assert probability.shape[1:]==images.shape[2:]
    assert np.isfinite(probability).all()
    assert ((probability>=0)&(probability<=1)).all()
    assert p_dates==[dates[t] for t in te]
    assert np.array_equal(y_saved>.5,wet[te]),"Test labels do not match image-derived proxies"
    assert np.array_equal(mask_saved>.5,observed[te]),"Test clouds/validity do not match imagery"
    cal=report.get("calibration_fit_on_validation_only",{})
    assert cal.get("source")=="VALIDATION MONTHS ONLY"
    assert cal["observed_validation_pixels"]==int(observed[va].sum())
    assert cal["observed_wet_pixels"]==int(wet[va].sum())
    fair=np.stack([observed[t]&observed[t-1]&observed[t-12] for t in te])
    truth=wet[te]
    baselines={
      "model":probability,
      "persistence":np.stack([wet[t-1] for t in te]),
      "seasonal_12m":np.stack([wet[t-12] for t in te])
    }
    metrics={}
    for name,pred in baselines.items():
        a=pred[fair].astype(float);b=truth[fair]
        binary=a>=.5
        tp=int((binary&b).sum());fp=int((binary&~b).sum())
        fn=int((~binary&b).sum());tn=int((~binary&~b).sum())
        brier=float(np.mean((a-b.astype(float))**2))
        saved=report["same_pixel_model_vs_both_baselines"]["metrics"][name]
        assert abs(brier-saved["brier"])<1e-6,name+" brier changed"
        assert saved["evaluated_pixels"]==int(fair.sum())
        for key,value in (("tp",tp),("fp",fp),("fn",fn),("tn",tn)):
            assert saved["confusion"][key]==value,name+" confusion matrix changed"
        metrics[name]={"brier":brier,"f1":2*tp/(2*tp+fp+fn) if tp+fn else None,
                       "tp":tp,"fp":fp,"fn":fn,"tn":tn}
    assert len(monthly["monthly"])==len(dates)
    assert monthly["ground_truth_verified"] is False
    assert monthly["hydraulic_connectivity_measured"] is False
    area=float(monthly["pixel_area_km2"])
    assert 0<area<1
    for i,item in enumerate(monthly["monthly"]):
        assert item["month"]==dates[i]
        assert abs(item["observed_fraction"]-float(observed[i].mean()))<1e-9
        assert abs(item["proxy_wet_observed_area_km2"]-int(wet[i].sum())*area)<1e-6
        if i:
            shared=observed[i]&observed[i-1]
            if shared.mean()>=.2:
                changes=int((wet[i]&~wet[i-1]&shared).sum())-int((wet[i-1]&~wet[i]&shared).sum())
                assert abs(item["observed_wet_change_km2"]-changes*area)<1e-6
            else:assert item["observed_wet_change_km2"] is None
    assert report["scientific_readiness_gate"]["ready_for_operational_or_ecological_decisions"] is False
    return {"artifact_integrity":"PASS","field_validated":False,
            "operationally_usable":False,
            "dataset_sha256":digest,
            "months":len(dates),
            "acquired_scenes":sum(len(m["scenes"]) for m in manifest["months"]),
            "train_targets":len(tr),"validation_targets":len(va),"test_targets":len(te),
            "shared_test_pixels":int(fair.sum()),"shared_test_proxy_wet_pixels":int(truth[fair].sum()),
            "independent_metrics":metrics,
            "beats_persistence_brier":metrics["model"]["brier"]<metrics["persistence"]["brier"],
            "caveat":"Technical integrity only. Proxy labels, not independently surveyed marsh water."}

def main():
    p=argparse.ArgumentParser()
    for name in ("data","manifest","evaluation","predictions","monitor","out"):
        p.add_argument("--"+name,required=True,type=Path)
    a=p.parse_args()
    result=verify(a.data,a.manifest,a.evaluation,a.predictions,a.monitor)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
