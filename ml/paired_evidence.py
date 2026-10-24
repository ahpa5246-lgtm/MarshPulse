"""Paired, month-block validation evidence for Mash Plus, never field certification.

Clustered pixels and adjacent months violate IID assumptions. We resample
contiguous *months within each independent named training region*, not individual
pixels. The confidence interval is descriptive and remains optimism-biased
after repeated checkpoint selection on the SAME chronological validation set.
"""
from __future__ import annotations
import numpy as np

def _weighted_gain(rows):
    n=sum(row[1] for row in rows)
    return sum(gain*weight for gain,weight in rows)/n if n else None

def monthly_paired_brier_evidence(by_region,repeats=1000,seed=20261024,block_length=2):
    if not isinstance(by_region,dict) or len(by_region)<2:
        raise ValueError("At least two real region reports needed for regional block uncertainty")
    if not 100<=repeats<=10000 or not 1<=block_length<=6:
        raise ValueError("Invalid block bootstrap configuration")
    grouped={}
    total_months=0
    for region,report in sorted(by_region.items()):
        if not isinstance(report,dict) or "months" not in report:
            raise ValueError("Missing monthly pairs for "+str(region))
        rows=[]
        for month in report["months"]:
            gain=month.get("all_observed_brier_gain_vs_soft_persistence")
            n=month.get("observed_pixels")
            if gain is None or not isinstance(n,(int,float)) or n<1:
                continue
            if not np.isfinite(gain) or not np.isfinite(n):
                raise ValueError("Nonfinite Brier comparison")
            rows.append((float(gain),int(n)))
        if len(rows)<6:
            return {"status":"INSUFFICIENT_MONTHS","regions":len(by_region),
                    "months":sum(len(x) for x in grouped.values())+len(rows),
                    "field_validated":False,
                    "confidence_interval_interpretation":"Not estimable from sufficient monthly blocks"}
        grouped[region]=rows
        total_months+=len(rows)
    all_rows=[r for rows in grouped.values() for r in rows]
    observed=_weighted_gain(all_rows)
    rng=np.random.default_rng(seed)
    samples=np.zeros(repeats)
    for i in range(repeats):
        selected=[]
        for rows in grouped.values():
            count=len(rows)
            # Resample contiguous overlapping blocks with circular indices
            # within each region; never mix neighboring-area pixels as IID.
            sampled=[]
            while len(sampled)<count:
                start=int(rng.integers(0,count))
                sampled.extend(rows[(start+k)%count] for k in range(block_length))
            selected.extend(sampled[:count])
        samples[i]=_weighted_gain(selected)
    lo,hi=np.quantile(samples,[.025,.975]).tolist()
    n_positive=sum(gain>0 for gain,n in all_rows)
    return {"status":"VALIDATION_ONLY_DESCRIPTIVE",
            "best_model_brier_gain_over_smoothed_persistence":observed,
            "month_block_95pct_interval":[float(lo),float(hi)],
            "fraction_resamples_positive":float((samples>0).mean()),
            "n_region_month_pairs":total_months,
            "n_positive_months":n_positive,
            "regions":len(grouped),
            "repeat_count":repeats,"block_length_months":block_length,
            "validation_skill_supported":bool(lo>0 and observed>=.0005),
            "field_validated":False,
            "warning":"Repeated training/selection on these same validation months invalidates a formal post-selection confidence claim; these are descriptive block-resampled intervals, not final independent test CIs."}
