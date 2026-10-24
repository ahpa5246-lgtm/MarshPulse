"""Pure-array tests for Landsat QA and cross-sensor comparability (synthetic only)."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from landsat_crosscheck import landsat_clear_qa,compare_arrays

class IndependentSensorTests(unittest.TestCase):
    def test_qa_rejects_all_cloud_related_bits_including_snow(self):
        q=np.array([[0,1,2,4],[8,16,32,128]],dtype=np.uint16)
        clear=landsat_clear_qa(q)
        self.assertTrue(clear[0,0])
        self.assertTrue(clear[1,3])  # water flag is not used as a label
        self.assertEqual(int(clear.sum()),2)

    def test_no_shared_observations_is_inconclusive(self):
        arr=np.zeros((6,4,4),dtype=np.float32)
        result=compare_arrays(arr,arr,arr,arr>0,arr>0,[f"2025-{m:02d}" for m in range(1,7)])
        self.assertEqual(result["status"],"INCONCLUSIVE_INSUFFICIENT_SUPPORT")
        self.assertFalse(result["reliability_certified"])

    def test_forecast_and_baseline_same_pixels(self):
        labels=np.zeros((6,4,4),dtype=bool);labels[:,:,0]=True
        predictions=np.where(labels,.95,.05)
        baseline=np.full((6,4,4),.05)
        good=np.ones((6,4,4),bool)
        result=compare_arrays(predictions,baseline,labels,good,good,
                              [f"2025-{m:02d}" for m in range(1,7)])
        self.assertEqual(result["model"]["evaluated_pixels"],result["persistence"]["evaluated_pixels"])
        self.assertGreater(result["model"]["f1"],result["persistence"]["f1"])
        self.assertEqual(result["status"],"INCONCLUSIVE_INSUFFICIENT_SUPPORT")
        self.assertFalse(result["independent_field_labels"])

if __name__=="__main__":
    unittest.main()
