"""Independent annotation evidence requires real human work; fixtures only."""
import csv,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from human_reference_evaluation import paired_human_review

FIELDS=["sample_id","month","latitude","longitude",
        "reference_image_source","reference_image_date",
        "human_open_water_0_or_1_or_uncertain","reviewer_id"]
def write(path,rows):
    with open(path,"w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader();w.writerows(rows)
def make_rows(label,who):
    return [{"sample_id":f"MP-{i+1:04d}","month":"2026-08",
             "latitude":"32.2","longitude":"45.46",
             "reference_image_source":"high-resolution-photo-source",
             "reference_image_date":"2026-08-16",
             "human_open_water_0_or_1_or_uncertain":label[i],
             "reviewer_id":who}for i in range(len(label))]
class HumanReferenceTests(unittest.TestCase):
    def test_two_actual_review_files_required_and_disagreement_counted(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            row=make_rows(["","",""],"")[0]
            q=make_rows(["0","0","0"],"")
            a=make_rows(["1","0","uncertain"],"annotator-a")
            b=make_rows(["1","1","0"],"annotator-b")
            write(d/"queue.csv",q);write(d/"a.csv",a);write(d/"b.csv",b)
            r=paired_human_review(d/"queue.csv",d/"a.csv",d/"b.csv")
            self.assertEqual(r["agreement_count"],1)
            self.assertEqual(len(r["disagreements"]),1)
            self.assertEqual(len(r["uncertain"]),1)
            self.assertEqual(r["agreed_labels"]["MP-0001"],1)
            self.assertFalse(r["estimated_area_accuracy_allowed"])
    def test_same_reviewer_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            write(d/"queue.csv",make_rows(["0"],""))
            write(d/"a.csv",make_rows(["0"],"same"))
            write(d/"b.csv",make_rows(["0"],"same"))
            with self.assertRaises(ValueError):
                paired_human_review(d/"queue.csv",d/"a.csv",d/"b.csv")
    def test_undated_image_or_missing_sample_refused(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            write(d/"queue.csv",make_rows(["0","1"],""))
            write(d/"a.csv",make_rows(["0"],"a"))
            write(d/"b.csv",make_rows(["0"],"b"))
            with self.assertRaises(ValueError):
                paired_human_review(d/"queue.csv",d/"a.csv",d/"b.csv")
            aa=make_rows(["0","1"],"a")
            aa[0]["reference_image_date"]="2020-01-01"
            write(d/"a.csv",aa)
            write(d/"b.csv",make_rows(["0","1"],"b"))
            with self.assertRaises(ValueError):
                paired_human_review(d/"queue.csv",d/"a.csv",d/"b.csv")
if __name__=="__main__":unittest.main()
