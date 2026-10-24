"""Real PyTorch forward-only forecast correctness, synthetic fixtures not field truth."""
import sys,tempfile,unittest
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from marshnet_v3 import MarshNetV3
from forecast_next_month import forward_forecast,run,TRAIN_NAMES
from train_v3 import smoke_data,load_region,stats

class FutureForecastTests(unittest.TestCase):
    def test_no_future_frame_and_exact_initial_persistence(self):
        net=MarshNetV3(base=8)
        x=np.zeros((4,7,32,32),dtype=np.float32)
        x[:,6]=1.;x[:,4]=.1;x[:,5]=-.2
        x[-1,5,4,5]=.5
        p,base=forward_forecast(net,x,np.zeros(6,dtype=np.float32),np.ones(6,dtype=np.float32))
        self.assertEqual(p.shape,(32,32))
        self.assertTrue(np.allclose(p,base,atol=2e-6))
        x[-1,6,1,1]=0
        p2,b2=forward_forecast(net,x,np.zeros(6),np.ones(6))
        self.assertAlmostEqual(float(p2[1,1]),.5,places=5)
    def test_reject_bad_history_and_normalization(self):
        net=MarshNetV3(base=8)
        with self.assertRaises(ValueError):
            forward_forecast(net,np.zeros((1,7,32,32)),np.zeros(6),np.ones(6))
        with self.assertRaises(ValueError):
            forward_forecast(net,np.zeros((4,7,32,32)),np.zeros(6),np.zeros(6))
    def test_end_to_end_test_forecast_uses_best_saved_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            regions=[]
            for i,name in enumerate(TRAIN_NAMES):
                p=root/"source_imagery"/name/"hawizeh_s2_monthly.npz"
                smoke_data(p,i)
                regions.append(load_region(p,synthetic=True))
            net=MarshNetV3(base=8)
            initial={"protocol":"mash-plus-daily-v1","field_validated":False,
                "architecture":{"lookback":4,"base":8},
                "train_data_sha256":[r["sha"] for r in regions],
                "best_weights":net.state_dict()}
            path=root/"daily_continuation_state.pt"
            torch.save(initial,path)
            result=run(path,root,root/"forecast",synthetic_smoke=True)
            self.assertTrue(result["source_only_prior_images"])
            self.assertFalse(result["future_target_labels_used"])
            for name in TRAIN_NAMES:
                info=result["forecasts"][name]
                self.assertEqual(info["forecast_month"],"2026-05")
                self.assertTrue((root/"forecast"/info["file"]).exists())
            self.assertTrue((root/"forecast"/"forecast_provenance.json").exists())

if __name__=="__main__":unittest.main()
