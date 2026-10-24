"""MarshNet V3 regression checks: persistence anchoring, no future leakage,
chronological partitioning, and spatial holdout disjointness."""
import unittest,sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from marshnet_v3 import MarshNetV3,prior_probability,masked_brier_bce
from train_v3 import split,disjoint_bbox,smoke_data,load_region,History,stats
class V3Tests(unittest.TestCase):
    def test_model_exact_soft_baseline_at_initialization(self):
        net=MarshNetV3(base=8)
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
if __name__=="__main__":unittest.main()
