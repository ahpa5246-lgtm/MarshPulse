"""Tests for conservative monthly imagery monitoring; no fake hydrology."""
import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from monitor_wetland import components8,monitor
class MonitoringTests(unittest.TestCase):
    def test_clusters_are_connected_pixels_not_hydraulic(self):
        x=np.zeros((6,6),bool);x[0,0]=True;x[1,1]=True;x[5,5]=True
        self.assertEqual(sorted(components8(x)),[1,2])
    def test_area_and_temporal_change_use_shared_observations(self):
        a=np.zeros((2,7,4,4),np.float32);a[:,6]=1
        a[:,4]=0;a[:,5]=-.2
        a[0,5,0,0]=.5;a[1,5,0,1]=.5
        a[1,6,0,0]=0 # old wet pixel becomes clouded; cannot call it a loss
        p=monitor(a,["2024-01","2024-02"],100.,minimum_coverage=.1)
        m=p["monthly"]
        self.assertAlmostEqual(m[0]["proxy_wet_observed_area_km2"],.01)
        self.assertAlmostEqual(m[1]["proxy_wet_observed_area_km2"],.01)
        self.assertAlmostEqual(m[1]["new_wet_km2"],.01)
        self.assertAlmostEqual(m[1]["no_longer_wet_km2"],0.)
        self.assertEqual(m[1]["change_note"],"MATCHED_OBSERVED_PIXELS_ONLY_NOT_AOI_TOTAL")
        self.assertFalse(p["hydraulic_connectivity_measured"])
    def test_low_clear_overlap_suppresses_change(self):
        a=np.zeros((2,7,4,4),np.float32);a[:,5]=-.2
        a[0,6,:2]=1;a[1,6,2:]=1
        report=monitor(a,["2024-01","2024-02"],20.)
        self.assertIsNone(report["monthly"][1]["observed_wet_change_km2"])
        self.assertEqual(report["monthly"][1]["change_note"],"INSUFFICIENT_MATCHED_CLEAR_PIXELS")
    def test_unit_validation(self):
        with self.assertRaises(ValueError):
            monitor(np.zeros((2,7,4,4)),["a","b"],-1)
if __name__=="__main__":unittest.main()
