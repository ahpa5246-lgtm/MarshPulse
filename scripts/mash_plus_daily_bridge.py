#!/usr/bin/env python3
"""GitHub Actions to Kaggle DAILY continuation bridge, through 2026-11-15.

Security: Kaggle API token is provided ONLY as GitHub Actions secret KAGGLE.
One notebook + private training-only dataset; never publish source manifests
with personal credentials or let Kaggle re-train over its sealed test sets.
"""
from __future__ import annotations
import argparse,datetime as dt,json,os,re,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from daily_bundle import initial_from_v4,validate_bundle,NAME
USER="minahussain111"
KERNEL=f"{USER}/mash-plus-daily-trainer"
DATASET=f"{USER}/mash-plus-daily-state"
SOURCE=f"{USER}/mash-plus-v4-independent-dalmaj"
START=dt.date(2026,10,24)
END=dt.date(2026,11,15)

def execute(*args,optional=False):
    cmd=["kaggle",*map(str,args)]
    proc=subprocess.run(cmd,text=True,capture_output=True,timeout=480)
    # Kaggle CLI must not echo any token in command lines or output.
    if proc.returncode!=0:
        if optional and re.search(r"404|not found|does not exist|no kernel|cannot find",proc.stdout+" "+proc.stderr,re.I):
            return None
        raise RuntimeError("Kaggle CLI operation failed: "+cmd[1]+" "+cmd[2]+": "+
                           (proc.stderr or proc.stdout)[-1400:])
    return proc.stdout+"\n"+proc.stderr

def version_status():
    # Private notebooks that do not exist yet may yield 403 rather than 404.
    # Verify the owner's authenticated notebook listing before treating this
    # as a first run; an existing inaccessible kernel must remain an error.
    listing=execute("kernels","list","--mine","--page","1","--csv")
    if KERNEL.split("/",1)[1] not in (listing or "").lower():
        return "ABSENT"
    status=execute("kernels","status",KERNEL)
    if status is None:raise RuntimeError("Owned Kaggle kernel listed but status unavailable")
    for flag in ("COMPLETE","ERROR","CANCELLED","RUNNING","QUEUED","PENDING"):
        if f"KernelWorkerStatus.{flag}" in status:return flag
    raise RuntimeError("Unknown Kaggle daily kernel status: "+status[-500:])

def output_zip(notebook,out,name):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    execute("kernels","output",notebook,"--force","--page-size","100",
            "--file-pattern",re.escape(name),"-p",str(out))
    items=list(out.rglob(name))
    if len(items)!=1:raise RuntimeError(f"{notebook} lacks exactly one completed {name} output")
    return items[0]

def write_metadata(folder):
    info={"title":"Mash Plus Daily State",
          "subtitle":"Private ESA Sentinel training caches and research-only optimizer checkpoints",
          "description":"Private continuation cache of ESA Copernicus Sentinel-derived pilot arrays, 3 training areas only. Not human field truth. Copernicus Sentinel Data Terms and Conditions. Kaggle source: Mash Plus.",
          "id":DATASET,"licenses":[{"name":"other"}]}
    (Path(folder)/"dataset-metadata.json").write_text(json.dumps(info,indent=2),encoding="utf8")

def publish_dataset(state_zip,workspace,exists,day):
    stage=Path(workspace)/"private-dataset"
    stage.mkdir(exist_ok=True,parents=True)
    shutil.copyfile(state_zip,stage/NAME)
    write_metadata(stage)
    validate_bundle(stage/NAME)
    if exists:
        execute("datasets","version","-p",str(stage),"-m",f"Mash Plus continuous training: source completed {day} — research only")
    else:
        execute("datasets","create","-p",str(stage))
    ready=execute("datasets","status",DATASET)
    print("PRIVATE_KAGGLE_DATASET_SYNC",DATASET,"status",(ready or "").strip()[-250:],flush=True)

def prepare_kernel(work):
    stage=Path(work)/"private-kernel";stage.mkdir(exist_ok=True,parents=True)
    src=Path("kaggle/Mash_Plus_Daily_Trainer.ipynb")
    data=json.loads(src.read_text(encoding="utf8"))
    if data.get("nbformat")!=4 or len(data.get("cells",[]))<8:
        raise ValueError("Invalid canonical daily Kaggle notebook")
    name="Mash_Plus_Daily_Trainer.ipynb"
    shutil.copyfile(src,stage/name)
    execute("kernels","init","-p",str(stage))
    metadata_path=stage/"kernel-metadata.json"
    metadata=json.loads(metadata_path.read_text(encoding="utf8"))
    template=str(metadata.get("id",""))
    if not template.startswith(USER+"/"):
        raise ValueError("Refusing to upload a notebook to a different account")
    metadata.update({
        "id":KERNEL,"title":"Mash Plus Daily Trainer",
        "code_file":name,"language":"python","kernel_type":"notebook",
        "is_private":"true","enable_gpu":"true","enable_internet":"true",
        "dataset_sources":[DATASET],"competition_sources":[],"kernel_sources":[],
        "model_sources":[]})
    metadata_path.write_text(json.dumps(metadata,indent=2),encoding="utf8")
    return stage

def state_day(state_zip):
    manifest=validate_bundle(state_zip)
    with zipfile.ZipFile(state_zip) as z:
        if "daily_training_report.json" not in z.namelist():return None
        report=json.loads(z.read("daily_training_report.json"))
    day=report.get("run_date_utc")
    return dt.date.fromisoformat(day) if day else None

def run(today,work):
    if today<START or today>END:
        print("DATE_GUARD_SKIP",today,"allowed",START,"through",END,flush=True)
        return "STOPPED_OUTSIDE_DATE_RANGE"
    if not os.environ.get("KAGGLE_API_TOKEN","").startswith("KGAT_"):
        raise RuntimeError("Expected KGAT_ Kaggle token in GitHub Actions KAGGLE secret; do not print key")
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    status=version_status()
    print("PREVIOUS_DAILY_KAGGLE_STATUS",status,flush=True)
    if status in ("RUNNING","QUEUED","PENDING"):
        print("SAFE_SKIP_ALREADY_RUNNING — do not overwrite notebook or checkpoint",flush=True)
        return "SKIP_RUNNING"
    if status in ("ERROR","CANCELLED"):
        raise RuntimeError("Previous daily Kaggle kernel ended with ERROR/CANCELLED. State not overwritten; inspect Kaggle logs.")
    owned_datasets=execute("datasets","list","--mine","-v")
    existing=DATASET.split("/",1)[1] in (owned_datasets or "").lower()
    if existing:
        execute("datasets","status",DATASET)
    if status=="ABSENT":
        if not existing:
            previous=execute("kernels","status",SOURCE)
            if "KernelWorkerStatus.COMPLETE" not in previous:
                raise RuntimeError("V4 real source experiment incomplete; cannot safely seed private daily state")
            archive=output_zip(SOURCE,work/"v4-evidence","Mash_Plus_V4_Real_Research.zip")
            bundle=initial_from_v4(archive,work/"initial"/NAME)
            publish_dataset(bundle,work,exists=False,day="V4 real data")
        # Dataset already exists after a partial publish; reuse rather than recreate.
    else:
        prior=output_zip(KERNEL,work/"previous-complete",NAME)
        if state_day(prior)==today:
            print("SAFE_SKIP_ALREADY_FINISHED_TODAY",today,flush=True)
            return "SKIP_DUPLICATE_DATE"
        # The previous notebook COMPLETED, with an immutable new checkpoint.
        # Only now may the next private Kaggle dataset version be created.
        # If publication of this dataset fails, the next notebook MUST NOT start.
        publish_dataset(prior,work,exists=existing,day=str(state_day(prior) or "prior"))
    stage=prepare_kernel(work)
    execute("kernels","push","-p",str(stage),"--accelerator","NvidiaTeslaT4")
    print("KAGGLE_DAILY_GPU_REQUEST_ACCEPTED",KERNEL,
          "but results UNVERIFIED until completed; days through",END,flush=True)
    return "GPU_REQUESTED"

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--date",default=dt.datetime.now(dt.timezone.utc).date().isoformat())
    p.add_argument("--work",type=Path,default=Path("/tmp/mash-plus-daily"))
    args=p.parse_args()
    print("BRIDGE_RESULT",run(dt.date.fromisoformat(args.date),args.work))
