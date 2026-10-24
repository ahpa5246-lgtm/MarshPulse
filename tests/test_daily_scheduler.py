"""Kaggle schedule safety: four distinct slots, never overlap or duplicate."""
import datetime as dt,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import mash_plus_daily_bridge as bridge

class DailySchedulerTests(unittest.TestCase):
    def test_exactly_four_independent_baghdad_slots(self):
        expected={"15 2 * * *":"05:15","15 6 * * *":"09:15",
                  "15 10 * * *":"13:15","15 14 * * *":"17:15"}
        self.assertEqual(bridge.SLOTS,expected)
        self.assertEqual(bridge.scheduled_slot(""),"manual")
        for cron,local in expected.items():
            self.assertEqual(bridge.scheduled_slot(cron),local)
        with self.assertRaises(ValueError):
            bridge.scheduled_slot("0 * * * *")
    @patch.dict(os.environ,{"KAGGLE_API_TOKEN":"KGAT_TEST_FAKE_NEVER_USED"})
    def test_same_slot_completed_skips_but_next_slot_can_resume(self):
        date=dt.date(2026,10,25)
        with patch.object(bridge,"version_status",return_value="COMPLETE"), \
             patch.object(bridge,"execute",return_value="mash-plus-daily-state"), \
             patch.object(bridge,"output_zip",return_value=Path("/fake/zip")), \
             patch.object(bridge,"completed_training_report",return_value={
                 "session_id":"2026-10-25_0515"}), \
             patch.object(bridge,"publish_dataset") as publish, \
             patch.object(bridge,"prepare_kernel",return_value=Path("/fake/kernel")) as kernel:
            self.assertEqual(bridge.run(date,Path("/tmp/test-mp-slot"),"05:15"),"SKIP_DUPLICATE_SESSION")
            publish.assert_not_called()
            self.assertEqual(bridge.run(date,Path("/tmp/test-mp-slot"),"09:15"),"GPU_REQUESTED")
            publish.assert_called_once()
            kernel.assert_called_once_with(Path("/tmp/test-mp-slot"),"2026-10-25_0915","2026-10-25")
    @patch.dict(os.environ,{"KAGGLE_API_TOKEN":"KGAT_TEST_FAKE_NEVER_USED"})
    def test_busy_previous_kernel_never_starts_another(self):
        with patch.object(bridge,"version_status",return_value="RUNNING"), \
             patch.object(bridge,"execute") as kaggle:
            self.assertEqual(bridge.run(dt.date(2026,10,25),Path("/tmp/no-run"),"13:15"),"SKIP_RUNNING")
            kaggle.assert_not_called()
    def test_date_guard_past_cutoff(self):
        self.assertEqual(bridge.run(dt.date(2026,11,16),Path("/tmp/no-run"),"05:15"),"STOPPED_OUTSIDE_DATE_RANGE")
    def test_outside_controlled_slot_is_rejected(self):
        with self.assertRaises(ValueError):
            bridge.run(dt.date(2026,10,25),Path("/tmp/no-run"),"23:15")

if __name__=="__main__":unittest.main()
