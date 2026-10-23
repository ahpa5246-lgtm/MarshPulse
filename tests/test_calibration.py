"""Unit checks for validation-only MarshNet probability calibration."""
import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from calibration import fit_validation_calibration,apply_calibration

class CalibrationTests(unittest.TestCase):
    def test_recalibration_cannot_increase_validation_brier_on_fitted_sample(self):
        z=np.linspace(-1.4,2.3,120,dtype=float).reshape(10,12)
        truth=(z>.9).astype(float)
        mask=np.ones_like(z)
        fit=fit_validation_calibration(z,truth,mask)
        self.assertEqual(fit["method"],"regularized-validation-grid")
        self.assertLessEqual(fit["calibrated_validation_brier"],fit["raw_validation_brier"]+1e-9)
        self.assertEqual(fit["observed_validation_pixels"],120)
    def test_unbalanced_validation_does_not_overclaim(self):
        z=np.zeros((4,4));truth=np.zeros_like(z);mask=np.ones_like(z)
        fit=fit_validation_calibration(z,truth,mask)
        self.assertEqual(fit["method"],"identity")
        self.assertEqual(fit["offset"],0.)
    def test_shape_and_mask_guard(self):
        with self.assertRaises(ValueError):
            fit_validation_calibration(np.ones((2,2)),np.ones((1,4)),np.ones((2,2)))
    def test_probability_is_bounded(self):
        p=apply_calibration(np.array([-1000.,0.,1000.]),{"temperature":2.,"offset":-.5})
        self.assertTrue(np.all((p>=0)&(p<=1)))
        self.assertEqual(p.shape,(3,))
if __name__=="__main__":unittest.main()
