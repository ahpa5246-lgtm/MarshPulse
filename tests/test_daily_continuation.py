"""Daily training is stateful, study-area isolated, and fail-closed.

Synthetic fixtures are NOT accuracy evidence or an independent field dataset.
"""
import sys,tempfile,unittest,zipfile,json
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from daily_bundle import allowed_source_names,initial_from_v4,validate_bundle,extract_train_only,updated_after_training
from daily_train import prepare_region_paths,validate_training_history,metric_gate,run
from train_v3 import smoke_data
from argparse import Namespace

class DailyContinuationTests(unittest.TestCase):
    def test_only_train_areas_allowed_and_untouched_holdout_is_forbidden(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for i,area in enumerate(("hawizeh_train","central_train","sinnaf_train")):
                smoke_data(root/"source_imagery"/area/"hawizeh_s2_monthly.npz",i)
            self.assertEqual(len(prepare_region_paths(root)),3)
            (root/"source_imagery"/"dalmaj_spatial_test").mkdir()
            with self.assertRaises(ValueError):prepare_region_paths(root)
    def test_model_gate_rejects_tiny_brier_gain_and_same_f1(self):
        self.assertFalse(metric_gate(.0099,.6,.01,.6,200))
        self.assertFalse(metric_gate(.0095,.65,.01,.6,4))
        self.assertTrue(metric_gate(.008,.7,.01,.6,200))
    def test_checkpoint_architecture_and_dataset_sha_must_match(self):
        state={"protocol":"mash-plus-daily-v1",
               "train_data_sha256":["x","y","z"],"architecture":{"base":16},
               "training_days":1}
        self.assertIs(validate_training_history(state,["x","y","z"],{"base":16}),state)
        with self.assertRaises(ValueError):validate_training_history(state,["x","y","wrong"],{"base":16})
    def test_real_v4_archive_seed_never_copies_spatial_holdout(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/"upstream.zip"
            with zipfile.ZipFile(source,"w") as z:
                for name in allowed_source_names():z.writestr(name,b"source")
                z.writestr("source_imagery/dalmaj_spatial_test/hawizeh_s2_monthly.npz",b"SEAL")
            outfile=root/"state.zip"
            initial_from_v4(source,outfile)
            self.assertEqual(validate_bundle(outfile)["status"],"TRAIN_ONLY_NEVER_FIELD_VALIDATED")
            with zipfile.ZipFile(outfile) as z:
                self.assertFalse(any("dalmaj" in name for name in z.namelist()))
    def test_genuine_training_smoke_resumes_optimizer_across_days(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for i,area in enumerate(("hawizeh_train","central_train","sinnaf_train")):
                smoke_data(root/"source_imagery"/area/"hawizeh_s2_monthly.npz",i)
            def args(out,existing=None):
                return Namespace(data=root,out=out,state_in=existing,v4_seed=None,
                       epochs=1,batch=3,lookback=4,base=8,seed=17,
                       lr=.0001,source_commit="unit-test-only",run_date="2026-10-24",synthetic_smoke=True,cpu=True)
            first=run(args(root/"day1"))
            second=run(args(root/"day2",root/"day1"/"daily_continuation_state.pt"))
            self.assertEqual(first["epochs_completed"],1)
            self.assertEqual(second["epochs_completed"],2)
            self.assertEqual(second["day_index"],2)
            checkpoint=torch.load(root/"day2"/"daily_continuation_state.pt",weights_only=True)
            self.assertEqual(checkpoint["training_days"],2)
            self.assertTrue(checkpoint["optimizer_state"]["state"])
            self.assertFalse(second["can_claim_generalization"])


    def test_three_stagnant_days_roll_back_same_best_epoch_weights(self):
        # Synthetic data and a deliberately impossible saved best Brier
        # force the rollback branch, rather than assuming random training loss.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for i,area in enumerate(("hawizeh_train","central_train","sinnaf_train")):
                smoke_data(root/"source_imagery"/area/"hawizeh_s2_monthly.npz",i)
            def args(out,existing=None):
                return Namespace(data=root,out=out,state_in=existing,v4_seed=None,
                       epochs=1,batch=3,lookback=4,base=8,seed=17,
                       lr=.0001,source_commit="synthetic-only",
                       run_date="2026-10-24",synthetic_smoke=True,cpu=True)
            run(args(root/"first"))
            state_path=root/"first"/"daily_continuation_state.pt"
            state=torch.load(state_path,weights_only=True)
            state["days_without_improvement"]=2
            state["best_validation_brier"]=0.0
            assert state["best_optimizer_state"] is not None
            torch.save(state,state_path)
            report=run(args(root/"rollback",state_path))
            self.assertTrue(report["rollback_to_validation_best"])
            self.assertFalse(report["optimizer_reset_on_legacy_rollback"])
            latest=torch.load(root/"rollback"/"daily_continuation_state.pt",weights_only=True)
            self.assertEqual(latest["days_without_improvement"],3)
            for name,param in latest["best_weights"].items():
                self.assertTrue(torch.equal(param,latest["current_weights"][name]))
            self.assertTrue(latest["best_optimizer_state"] is not None)

if __name__=="__main__":unittest.main()
