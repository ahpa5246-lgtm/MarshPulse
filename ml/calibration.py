"""Validation-only probability calibration for MarshNet V2.

Calibrate after checkpoint selection using ONLY validation months. Test targets
must not be inspected before calibration. Calibration cannot establish field truth.
"""
import numpy as np

def expit(x):
    a=np.asarray(x,dtype=np.float64)
    # np.clip prevents overflow while preserving binary probability ordering.
    return 1/(1+np.exp(-np.clip(a,-40,40)))

def apply_calibration(logits,params):
    return expit(np.asarray(logits,dtype=np.float64)/float(params["temperature"])+float(params["offset"]))

def fit_validation_calibration(logits,labels,mask,minimum_class_pixels=25):
    z=np.asarray(logits,dtype=np.float64)
    y=np.asarray(labels,dtype=np.float64)
    valid=np.asarray(mask,dtype=bool)
    if z.shape!=y.shape or y.shape!=valid.shape:
        raise ValueError("Calibration inputs must align")
    values=z[valid];truth=y[valid]
    positives=int((truth>=.5).sum())
    negatives=int(len(truth)-positives)
    result={"source":"VALIDATION MONTHS ONLY","observed_validation_pixels":len(truth),
            "observed_wet_pixels":positives,"observed_dry_pixels":negatives,
            "temperature":1.,"offset":0.,"method":"identity"}
    if positives<minimum_class_pixels or negatives<minimum_class_pixels:
        result["reason"]="Insufficient wet/dry validation examples; no calibration fitted"
        return result
    if not np.isfinite(values).all() or not np.isfinite(truth).all():
        raise ValueError("Nonfinite logits or validation targets")
    baseline=float(np.mean((expit(values)-truth)**2))
    # Small, deterministic grid — penalize extreme adjustments to a short
    # validation record; never fit from held-out/test months.
    best=baseline
    best_pair=(1.,0.)
    for temp in (.65,.8,1.,1.25,1.6,2.,2.8,4.,6.):
        for offset in np.arange(-3.5,1.51,.125):
            prob=expit(values/temp+offset)
            brier=float(np.mean((prob-truth)**2))
            penalty=.00015*(abs(np.log(temp))+abs(offset))
            score=brier+penalty
            if score<best-1e-7:
                best=score;best_pair=(float(temp),float(offset))
    temp,offset=best_pair
    calibrated=float(np.mean((apply_calibration(values,{"temperature":temp,"offset":offset})-truth)**2))
    result.update({"temperature":temp,"offset":offset,"method":"regularized-validation-grid",
                   "raw_validation_brier":baseline,
                   "calibrated_validation_brier":calibrated,
                   "reason":"Calibration fitted from validation labels; test labels untouched"})
    return result
