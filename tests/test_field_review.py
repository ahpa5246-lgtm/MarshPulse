"""Queue is NOT human ground truth: unit tests of stratification only."""
import unittest,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from prepare_field_review import neighborhood,stratified_cells

class HumanReviewPreparationTests(unittest.TestCase):
    def test_neighborhood_marks_dry_margin_but_not_wet_center(self):
        water=np.zeros((8,8),bool);water[4,4]=True
        boundary=neighborhood(water)
        self.assertEqual(int(boundary.sum()),4)
        self.assertFalse(boundary[4,4])
    def test_stratification_is_reproducible_and_may_be_incomplete(self):
        x=np.zeros((6,7,32,32),np.float32)
        x[:,4]=.2;x[:,5]=-.3;x[:,6]=1.
        x[:,4,12:16,12:16]=-.2;x[:,5,12:16,12:16]=.7
        date=[f"2025-{i:02d}" for i in range(1,7)]
        a,counts=stratified_cells(x,date,per_month=9,seed=17)
        b,_=stratified_cells(x,date,per_month=9,seed=17)
        self.assertEqual(a,b)
        self.assertGreater(counts["wet"],0)
        self.assertGreater(counts["dry"],0)
        self.assertEqual(len(a),54)
        self.assertNotIn("human_open_water_0_or_1",a[0])

if __name__=="__main__":unittest.main()
