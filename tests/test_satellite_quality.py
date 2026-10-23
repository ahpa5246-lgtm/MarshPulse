"""Deterministic science checks for wetland dataset audit + honest benchmarks."""
import unittest
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from quality_gate import audit_cube,binary_metrics,benchmark_temporal,readiness_verdict

def sample_cube(months=26):
    cube=np.zeros((months,7,8,8),dtype=np.float32)
    cube[:,6]=1
    cube[:,4]=.2
    cube[:,5]=-.2
    for t in range(months):
        cube[t,5,1:4,1:4]=.6 if t%4==0 else -.2
    return cube

class QualityGateTests(unittest.TestCase):
    def test_audit_counts_true_observations_not_clouds(self):
        cube=sample_cube()
        cube[0,6,0:2,0:2]=0
        summary=audit_cube(cube,[str(i) for i in range(26)])
        self.assertEqual(summary["months"][0]["observed_pixels"],60)
        self.assertEqual(summary["months"][0]["wet_pixels"],8)
        self.assertGreater(summary["months_with_wet_proxy"],0)
        self.assertTrue(summary["label_source"].startswith("UNVERIFIED"))
    def test_all_dry_is_warning_not_accuracy_victory(self):
        cube=sample_cube();cube[:,5]=-.5
        summary=audit_cube(cube)
        self.assertIn("NO_WET_PIXELS: cannot learn wet detection from this pilot",summary["warnings"])
        metrics=binary_metrics(np.zeros((2,3)),np.zeros((2,3)),np.ones((2,3)))
        self.assertIsNone(metrics["f1"])
        self.assertIsNone(metrics["balanced_accuracy"])
        self.assertEqual(metrics["status"],"ONE_CLASS_HOLDOUT")
    def test_comparable_baselines_restrict_to_shared_observed_pixels(self):
        x=sample_cube()
        x[12,6,1:4,1:4]=0
        x[24,6,3:7,3:7]=0
        # one wet month at t=24 and 12-month seasonal source t=12 masked
        pred=np.zeros((2,8,8),dtype=float)
        b=benchmark_temporal(x,[24,25],pred)
        n=b["metrics"]["model"]["evaluated_pixels"]
        self.assertEqual(n,b["metrics"]["persistence"]["evaluated_pixels"])
        self.assertEqual(n,b["metrics"]["seasonal_12m"]["evaluated_pixels"])
        self.assertLess(n,2*64)
        self.assertEqual(b["fairness"],"same target and observed pixels for all three methods")
    def test_readiness_never_deploys_without_field_truth_spatial_holdout(self):
        x=sample_cube(26)
        p=np.zeros((2,8,8))
        b=benchmark_temporal(x,[24,25],p)
        gate=readiness_verdict(b,audit_cube(x))
        self.assertFalse(gate["ready_for_operational_or_ecological_decisions"])
        self.assertFalse(gate["independent_reference"])
        self.assertEqual(gate["status"],"NOT_VALIDATED")
    def test_probability_validation(self):
        with self.assertRaises(ValueError):
            binary_metrics(np.array([1.5]),np.array([1.]),np.array([1]))
    def test_temporal_baseline_requires_full_year_lag(self):
        x=sample_cube()
        with self.assertRaises(ValueError):
            benchmark_temporal(x,[8],np.zeros((1,8,8)))
if __name__=="__main__":unittest.main()
