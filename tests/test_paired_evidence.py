"""Block bootstrap evidence tests — synthetic fixtures are never scientific scores."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from paired_evidence import monthly_paired_brier_evidence

def region(gains):
    return {"months":[{"month":f"2025-{i+1:02d}",
        "all_observed_brier_gain_vs_soft_persistence":float(g),
        "observed_pixels":100} for i,g in enumerate(gains)]}

class PairedEvidenceTests(unittest.TestCase):
    def test_uniform_improvement_has_strictly_positive_interval(self):
        r={"a":region([.003]*7),"b":region([.002]*7)}
        x=monthly_paired_brier_evidence(r,repeats=300)
        self.assertTrue(x["validation_skill_supported"])
        self.assertGreater(x["month_block_95pct_interval"][0],0)
        self.assertFalse(x["field_validated"])
    def test_uniform_worse_model_is_rejected(self):
        r={"a":region([-.003]*7),"b":region([-.002]*7)}
        x=monthly_paired_brier_evidence(r,repeats=300)
        self.assertFalse(x["validation_skill_supported"])
        self.assertLess(x["month_block_95pct_interval"][1],0)
    def test_few_months_fails_closed(self):
        x=monthly_paired_brier_evidence({"a":region([.01]*4),"b":region([.01]*4)})
        self.assertEqual(x["status"],"INSUFFICIENT_MONTHS")
        self.assertFalse(x["field_validated"])
    def test_no_independent_sites_is_invalid(self):
        with self.assertRaises(ValueError):
            monthly_paired_brier_evidence({"one":region([.001]*6)})
    def test_seed_reproducibility(self):
        r={"a":region([.03,-.01,.01,.02,-.005,.01]),"b":region([.01,.04,-.01,.005,-.01,.006])}
        x=monthly_paired_brier_evidence(r,300)
        y=monthly_paired_brier_evidence(r,300)
        self.assertEqual(x["month_block_95pct_interval"],y["month_block_95pct_interval"])

if __name__=="__main__":unittest.main()
