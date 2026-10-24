"""MarshNet V3 regression checks: persistence anchoring, no future leakage,
chronological partitioning, and spatial holdout disjointness."""
import unittest,sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from marshnet_v3 import MarshNetV3,prior_probability,masked_brier_bce
from train_v3 import split,disjoint_bbox,smoke_data,load_region,History,stats,benchmark,aggregate_f1,evaluation_checkpoint
from collect_sentinel import keys
class V3Tests(unittest.TestCase):
    def test_validation_selected_weights_are_always_evaluated(self):
        research={"w":torch.tensor([1.])}
        passed={"w":torch.tensor([2.])}
        chosen,role=evaluation_checkpoint(passed,research)
        self.assertIs(chosen,passed)
        self.assertEqual(role,"VALIDATION_PASSED_RESEARCH_ONLY")
        chosen,role=evaluation_checkpoint(None,research)
        self.assertIs(chosen,research)
        self.assertEqual(role,"REJECTED_RESEARCH_CHALLENGER")
        with self.assertRaises(ValueError):
            evaluation_checkpoint(None,None)

    def test_model_exact_soft_baseline_at_initialization(self):
        net=MarshNetV3(base=8)
        self.assertEqual(net.config["model_name"],"Mash Plus")
        self.assertEqual(net.config["model_version"],"V3")
        x=torch.zeros(1,4,7,32,32)
        prior=torch.full((1,32,32),.23)
        with torch.no_grad():got=net(x,prior).sigmoid()
        self.assertTrue(torch.allclose(got,prior,atol=1e-6))
    def test_prior_never_uses_future_month(self):
        x=torch.zeros(1,4,7,8,8)
        x[:,-1,4]=-.2;x[:,-1,5]=.7;x[:,-1,6]=1
        p=prior_probability(x)
        self.assertTrue(torch.allclose(p,torch.full_like(p,.99)))
        x[:,-1,6]=0
        self.assertTrue(torch.allclose(prior_probability(x),torch.full_like(p,.5)))
    def test_loss_ignores_cloudy_targets(self):
        a=torch.zeros(1,3,3)
        y=torch.zeros_like(a)
        m=torch.ones_like(a);m[:,0,0]=0
        loss=masked_brier_bce(a,y,m)
        a[:,0,0]=50
        self.assertTrue(torch.allclose(masked_brier_bce(a,y,m),loss))
        with self.assertRaises(ValueError):masked_brier_bce(a,y,torch.zeros_like(m))
    def test_chronological_no_test_peeking(self):
        tr,va,te=split(60,4)
        self.assertLess(max(tr),min(va))
        self.assertLess(max(va),min(te))
        self.assertGreaterEqual(min(tr),12)
    def test_aoi_overlap_is_rejected(self):
        a=[47.6,31.5,47.7,31.6]
        self.assertFalse(disjoint_bbox(a,[47.65,31.56,47.75,31.66]))
        self.assertTrue(disjoint_bbox(a,[47.7,31.56,47.8,31.66]))
    def test_soft_persistence_is_independent_baseline(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"pilot.npz";smoke_data(path)
            r=load_region(path,synthetic=True)
            _,_,te=split(28,4)
            prob=np.zeros((len(te),32,32),dtype=np.float32)
            metrics=benchmark(r,te,prob)["metrics"]
            self.assertIn("smoothed_persistence",metrics)
            self.assertEqual(metrics["model"]["evaluated_pixels"],
                             metrics["smoothed_persistence"]["evaluated_pixels"])
            self.assertLess(metrics["smoothed_persistence"]["brier"],
                            metrics["model"]["brier"])
    def test_training_history_excludes_target(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"pilot.npz";smoke_data(path)
            r=load_region(path,synthetic=True)
            tr,_,_=split(28,4)
            mean,std=stats([r],4)
            sample=History(r,[tr[0]],4,mean,std)[0]
            self.assertEqual(sample[0].shape,(4,7,32,32))
            self.assertEqual(sample[1].shape,(32,32))
            self.assertEqual(sample[2].shape,(32,32))
            self.assertEqual(sample[3].shape,(32,32))
    def test_input_month_validation_fails_closed(self):
        self.assertEqual(keys("2025-11","2026-02"),["2025-11","2025-12","2026-01","2026-02"])
        for start,end in (("2026-09","2026-08"),("2026-13","2027-01"),("2026-00","2026-03"),
                          ("wrong","2026-01"),("2000-01","2030-01")):
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):
                keys(start,end)
    def test_manifest_coverage_is_verified_against_source_arrays(self):
        import json
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"region.npz"
            smoke_data(path)
            with np.load(path,allow_pickle=False) as archive:
                dates=list(map(str,archive["dates"].tolist()))
            months=[{"month":d,"fraction_valid":1.0,"scenes":[{"item":f"S2_{i}"}]}
                    for i,d in enumerate(dates)]
            manifest=path.with_name("satellite_manifest.json")
            record={"source":"REAL ESA Sentinel-2 TEST FIXTURE (NOT ACTUAL SATELLITE)",
                    "months":months,"bbox_lonlat":[47.0,31.0,47.1,31.1]}
            manifest.write_text(json.dumps(record))
            self.assertIsNotNone(load_region(path)["manifest_sha"])
            record["months"][0]["fraction_valid"]=0.5
            manifest.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,"coverage mismatch"):
                load_region(path)
            record["months"][0]["fraction_valid"]=1.0
            record["months"][0]["scenes"]=[]
            manifest.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,"without identifiable"):
                load_region(path)
    def test_clouded_month_allowed_only_without_observed_pixels(self):
        import json
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"region.npz"
            smoke_data(path)
            with np.load(path,allow_pickle=False) as archive:
                cube=archive["x"].copy()
                dates=archive["dates"].copy()
                bands=archive["bands"].copy()
            cube[0,6]=0
            np.savez_compressed(path,x=cube,dates=dates,bands=bands)
            records=[{"month":str(d),"fraction_valid":0.0 if i==0 else 1.0,
                      "scenes":[] if i==0 else [{"item":f"S2_{i}"}]}
                     for i,d in enumerate(dates)]
            path.with_name("satellite_manifest.json").write_text(json.dumps({
               "source":"REAL ESA Sentinel-2 TEST FIXTURE (NOT ACTUAL SATELLITE)",
               "months":records,"bbox_lonlat":[47.0,31.0,47.1,31.1]}))
            self.assertEqual(load_region(path)["x"][0,6].sum(),0)
    def test_monthwise_evidence_keeps_correlated_months_separate(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"pilot.npz";smoke_data(path)
            region=load_region(path,synthetic=True)
            _,_,te=split(28,4)
            predictions=np.zeros((len(te),32,32),dtype=np.float32)
            scores=benchmark(region,te,predictions)
            self.assertEqual(scores["months_with_shared_observations"],len(te))
            self.assertEqual(len(scores["monthly_paired_scores"]),len(te))
            self.assertTrue(all(row["status"]=="OK" and row["shared_pixels"]>0
                                for row in scores["monthly_paired_scores"]))
    def test_wet_f1_pools_confusion_not_area_scores(self):
        a={"confusion":{"tp":5,"fp":2,"fn":3}}
        b={"confusion":{"tp":10,"fp":8,"fn":1}}
        self.assertAlmostEqual(aggregate_f1([a,b]),30/(30+10+4))
        self.assertIsNone(aggregate_f1([{"confusion":{"tp":0,"fp":0,"fn":0}}]))
    def test_synthetic_spatial_inputs_have_different_checksums(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            a=Path(tmp)/"first.npz";b=Path(tmp)/"second.npz"
            smoke_data(a,region_index=0);smoke_data(b,region_index=2)
            self.assertNotEqual(load_region(a,synthetic=True)["sha"],
                                load_region(b,synthetic=True)["sha"])

if __name__=="__main__":unittest.main()
