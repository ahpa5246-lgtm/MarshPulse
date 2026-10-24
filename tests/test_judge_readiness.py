"""Tests for evidence audit only; fixtures are artificial, NEVER model performance."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from judge_readiness import audit,markdown

def valid_fixture():
    def metrics(brier,f1):
        return {"status":"OK","brier":brier,"f1":f1,
                "precision":.77,"recall":.73,
                "wet_truth_pixels":240,"wet_prevalence":.12,"evaluated_pixels":2000}
    return {
      "model_name":"Mash Plus","model_version":"V3",
      "status":"REAL SATELLITE PROXY / NO FIELD VALIDATION",
      "data_provenance":[{"sha256":"a"*64,"manifest_sha256":"c"*64},
                         {"sha256":"b"*64,"manifest_sha256":"d"*64}],
      "spatial_test_provenance":{"sha256":"e"*64},
      "spatial_transfer_evaluated":True,
      "evaluated_neural_checkpoint":"VALIDATION_PASSED_RESEARCH_ONLY",
      "selected_champion":{"type":"Mash Plus V3","validation_challengers":[
         {"seed":17,"passed_validation_gate":True},
         {"seed":42,"passed_validation_gate":False}]},
      "independent_field_labels":False,
      "test_evaluations":[{"region":"spatial_holdout",
        "shared_observed_fraction":.9,
        "metrics":{"model":metrics(.13,.77),
                   "persistence":metrics(.19,.65),
                   "smoothed_persistence":metrics(.18,.65),
                   "seasonal_12m":metrics(.21,.54)},
        "monthly_paired_scores":[{"month":f"2025-{month:02d}","status":"OK",
            "wet_pixels":24,"candidate_minus_best_baseline":-.01}
            for month in range(1,8)]
      }]
    }

class ReadinessTests(unittest.TestCase):
    def test_promising_satellite_proxy_does_not_certify_field_reliability(self):
        result=audit(valid_fixture())
        self.assertEqual(result["status"],"PROMISING_PROXY_EXPERIMENT_NOT_FIELD_VALIDATED")
        self.assertFalse(result["field_or_operational_claim_permitted"])
        self.assertIn("NOT ESTABLISHED",markdown(result))

    def test_absent_or_rejected_model_fails_closed(self):
        fixture=valid_fixture()
        fixture["selected_champion"]["type"]="SMOOTHED_PERSISTENCE_BASELINE"
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_archived_research_seed_cannot_pose_as_champion(self):
        fixture=valid_fixture()
        fixture["evaluated_neural_checkpoint"]="REJECTED_RESEARCH_CHALLENGER"
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_wet_class_failure_cannot_hide_behind_brier(self):
        fixture=valid_fixture()
        fixture["test_evaluations"][0]["metrics"]["model"]["f1"]=.1
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_no_wet_test_examples_not_recognized_as_success(self):
        fixture=valid_fixture()
        fixture["test_evaluations"][0]["metrics"]["model"]["wet_truth_pixels"]=0
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_fake_provenance_rejected(self):
        fixture=valid_fixture()
        fixture["status"]="SYNTHETIC TEST ONLY"
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_sparse_monthly_support_rejected(self):
        fixture=valid_fixture()
        fixture["test_evaluations"][0]["monthly_paired_scores"]=[]
        self.assertEqual(audit(fixture)["status"],"NOT_DEMONSTRATED")

    def test_missing_report_fails_closed(self):
        self.assertEqual(audit(None)["status"],"NOT_DEMONSTRATED")

if __name__=="__main__":
    unittest.main()
