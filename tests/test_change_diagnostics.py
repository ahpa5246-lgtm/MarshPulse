"""Change diagnostics are satellite-label proxies; these fixtures are synthetic ONLY."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from change_diagnostics import transition_validation_report,aggregate_transition_reports
from quality_gate import wet_proxy

def scenario():
    x=np.zeros((16,7,8,8),dtype=np.float32)
    x[:,4]=0.1;x[:,5]=-.2;x[:,6]=1.
    x[11,5,1,1]=.6
    x[12,5,2,2]=.6  # New visible water
    x[13,5,2,2]=.6  # Stable water
    x[13,5,3,3]=.6  # A second flood
    x[14,5,4,4]=.6  # Another flood, and two previous points dry
    dates=[f"{2025+i//12:04d}-{i%12+1:02d}" for i in range(len(x))]
    targets=[12,13,14]
    wet,_=wet_proxy(x)
    p=np.stack([np.where(wet[t],.9,.1) for t in targets]).astype(float)
    return x,dates,targets,p

class ChangeDiagnosticsTests(unittest.TestCase):
    def test_perfect_event_model_detects_gain_and_drying(self):
        x,dates,indices,p=scenario()
        r=transition_validation_report(x,dates,indices,p)
        self.assertEqual(r["months_evaluated"],3)
        self.assertGreater(r["total_counts"]["wet_gain_pixels"],0)
        self.assertGreater(r["total_counts"]["drying_pixels"],0)
        self.assertAlmostEqual(r["transition_f1"],1.)
        self.assertAlmostEqual(r["gain_detection_recall"],1.)
        self.assertAlmostEqual(r["drying_detection_recall"],1.)
        self.assertGreater(r["brier_by_subset"]["change_persistence"],
                           r["brier_by_subset"]["change_model"])
    def test_persistence_has_zero_event_recall(self):
        x,dates,indices,_=scenario()
        wet,_=wet_proxy(x)
        prior=np.stack([np.where(wet[t-1],.99,.01) for t in indices])
        r=transition_validation_report(x,dates,indices,prior)
        self.assertEqual(r["transition_f1"],0)
        self.assertEqual(r["gain_detection_recall"],0)
    def test_diagnostic_uses_only_passed_validation_months(self):
        x,dates,indices,p=scenario()
        original=transition_validation_report(x,dates,indices[:2],p[:2])
        x[-1,5,:,:]=.9
        changed=transition_validation_report(x,dates,indices[:2],p[:2])
        self.assertEqual(original["total_counts"],changed["total_counts"])
    def test_no_fabricated_change_when_no_observed_pixels(self):
        x,dates,targets,p=scenario()
        x[:,6]=0
        r=transition_validation_report(x,dates,targets,p)
        self.assertEqual(r["total_counts"]["observed_pixels"],0)
        self.assertIsNone(r["transition_f1"])
        self.assertIsNone(r["brier_by_subset"]["stable_model"])
    def test_reject_invalid_predictions_and_bad_target_indices(self):
        x,dates,targets,p=scenario()
        with self.assertRaises(ValueError):
            transition_validation_report(x,dates,targets,p[:1])
        with self.assertRaises(ValueError):
            transition_validation_report(x,dates,[11],p[:1])
    def test_region_aggregate_keeps_provenance_and_no_field_claim(self):
        x,dates,targets,p=scenario()
        r=transition_validation_report(x,dates,targets,p)
        out=aggregate_transition_reports({"a":r,"b":r})
        self.assertEqual(out["regions"],2)
        self.assertFalse(out["field_validated"])
        self.assertEqual(out["total_counts"]["observed_pixels"],2*r["total_counts"]["observed_pixels"])

if __name__=="__main__":unittest.main()
