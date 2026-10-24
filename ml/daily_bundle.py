#!/usr/bin/env python3
"""Private Kaggle state ZIP: reproducible 3-area real-data cache + model weights.

Only explicitly allowlisted TRAIN sources leave the V4 experiment archive.
Dalmaj/Hammar imagery and labels are never available to daily fitting.
"""
from __future__ import annotations
import hashlib,json,zipfile
from pathlib import Path

REGIONS=("hawizeh_train","central_train","sinnaf_train")
NAME="Mash_Plus_Daily_State.zip"
def allowed_source_names():
    return tuple(f"source_imagery/{area}/{file}" for area in REGIONS
                 for file in ("hawizeh_s2_monthly.npz","satellite_manifest.json"))
def sha(data):
    return hashlib.sha256(data).hexdigest()
def validate_bundle(bundle):
    bundle=Path(bundle)
    with zipfile.ZipFile(bundle) as z:
        names=z.namelist()
        if len(set(names))!=len(names):raise ValueError("Duplicate ZIP entry names")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            raise ValueError("Unsafe or escaping ZIP member path")
        permitted=set(allowed_source_names())|{
            "v4_seed.pt","daily_continuation_state.pt","daily_training_report.json","bundle_manifest.json"}
        if set(names)-permitted:raise ValueError("Unexpected source/test data in daily training bundle")
        for name in allowed_source_names():
            if name not in names:raise ValueError("Missing required three-area real training source "+name)
        manifest=json.loads(z.read("bundle_manifest.json"))
        if manifest.get("status")!="TRAIN_ONLY_NEVER_FIELD_VALIDATED":
            raise ValueError("Research-only status label missing")
        for name,expected in manifest["sha256"].items():
            if sha(z.read(name))!=expected:raise ValueError("SHA integrity mismatch: "+name)
        return manifest
def initial_from_v4(v4_experiment_zip,out):
    out=Path(out)
    source=Path(v4_experiment_zip)
    with zipfile.ZipFile(source) as z:
        data={name:z.read(name) for name in allowed_source_names()}
        seed="evaluations/convgru/marshnet_v3_RESEARCH_ONLY.pt"
        if seed in z.namelist():data["v4_seed.pt"]=z.read(seed)
        info={"protocol":"mash-plus-daily-bundle-v1",
              "status":"TRAIN_ONLY_NEVER_FIELD_VALIDATED",
              "seed_from":"real Kaggle V4 independent-Dalmaj study (TRAIN AOIs ONLY)",
              "sha256":{name:sha(value) for name,value in data.items()}}
    data["bundle_manifest.json"]=json.dumps(info,indent=2).encode()
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for name,value in data.items():z.writestr(name,value)
    validate_bundle(out)
    return out
def updated_after_training(previous_bundle,trained_output,new_bundle):
    previous_bundle=Path(previous_bundle);trained_output=Path(trained_output)
    validate_bundle(previous_bundle)
    with zipfile.ZipFile(previous_bundle) as z:
        files={name:z.read(name) for name in allowed_source_names()}
        # Do not reuse original seed after training has continued.
    for name in ("daily_continuation_state.pt","daily_training_report.json"):
        path=trained_output/name
        if not path.is_file():raise ValueError("No completed daily checkpoint+report: "+name)
        files[name]=path.read_bytes()
    report=json.loads(files["daily_training_report.json"])
    if report.get("status")!="RESEARCH_ONLY_NOT_FIELD_VALIDATED" or report.get("geographic_test_used_for_training") is not False:
        raise ValueError("Refuse to archive unapproved or test-leaking training")
    info={"protocol":"mash-plus-daily-bundle-v1",
          "status":"TRAIN_ONLY_NEVER_FIELD_VALIDATED",
          "training_days":report["day_index"],
          "seed_from":"genuine Sentinel-2 training regions, original V4 evidence",
          "sha256":{name:sha(value) for name,value in files.items()}}
    files["bundle_manifest.json"]=json.dumps(info,indent=2).encode()
    target=Path(new_bundle);target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=3) as z:
        for name,blob in files.items():z.writestr(name,blob)
    validate_bundle(target)
    return target
def extract_train_only(bundle,destination):
    validate_bundle(bundle)
    destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(bundle) as z:
        for name in allowed_source_names()+("daily_continuation_state.pt","v4_seed.pt"):
            if name in z.namelist():
                dest=destination/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read(name))
    return destination

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--seed-from-v4",type=Path)
    p.add_argument("--verify",type=Path)
    p.add_argument("--out",type=Path)
    args=p.parse_args()
    if args.verify:print(json.dumps(validate_bundle(args.verify),indent=2))
    elif args.seed_from_v4 and args.out:
        print(initial_from_v4(args.seed_from_v4,args.out))
    else:p.error("Expected --verify or --seed-from-v4 and --out")
if __name__=="__main__":main()
