"""Test the ACTUAL transition training objective (synthetic correctness fixtures)."""
import sys,unittest
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from marshnet_v3 import masked_change_brier,masked_brier_bce
from train_v3 import History

class TransitionTrainingTests(unittest.TestCase):
    def test_transition_error_has_gradient_and_persistence_is_penalized(self):
        prior=torch.tensor([[[.99,.01],[.01,.99]]])
        labels=torch.tensor([[[0.,1.],[0.,1.]]])
        observed=torch.ones_like(labels)
        prev=torch.ones_like(labels)
        logits=torch.logit(prior).detach().clone().requires_grad_(True)
        loss=masked_change_brier(logits,labels,observed,prior,prev,strength=.2)
        self.assertGreater(float(loss),0)
        loss.backward()
        self.assertTrue(torch.isfinite(logits.grad).all())
        self.assertNotEqual(float(logits.grad.abs().sum()),0.0)
    def test_no_future_mask_and_no_change_returns_zero_with_finite_grad(self):
        prior=torch.full((1,2,2),.99)
        y=torch.ones_like(prior)
        logits=torch.logit(prior).detach().requires_grad_(True)
        loss=masked_change_brier(logits,y,torch.ones_like(y),prior,torch.ones_like(y))
        self.assertEqual(float(loss),0)
        loss.backward()
        self.assertTrue(torch.isfinite(logits.grad).all())
    def test_missing_previous_observation_not_treated_as_change(self):
        prior=torch.full((1,2,2),.5)
        y=torch.ones_like(prior)
        logits=torch.zeros_like(prior).requires_grad_(True)
        self.assertEqual(float(masked_change_brier(logits,y,torch.ones_like(y),prior,torch.zeros_like(y))),0)
    def test_mask_uncertain_targets_only_during_training(self):
        x=np.zeros((28,7,32,32),dtype=np.float32)
        x[:,6]=1.
        x[:,4]=.25
        x[:,5]=.5
        x[16,5,4,4]=.101
        x[16,4,4,4]=.299
        region={"x":x}
        mean=np.zeros((6,),dtype=np.float32)
        std=np.ones((6,),dtype=np.float32)
        train=History(region,[16],4,mean,std,augment=True,water_margin=.025,ndvi_margin=.025)
        test=History(region,[16],4,mean,std,augment=False,water_margin=.025,ndvi_margin=.025)
        train_mask=train[0][3]
        test_mask=test[0][3]
        self.assertLess(int(train_mask.sum()),int(test_mask.sum()))
        self.assertEqual(int(test_mask.sum()),32*32)
    def test_bad_shapes_and_training_mask_bounds_fail(self):
        bad=torch.zeros(1,3,3)
        with self.assertRaises(ValueError):
            masked_change_brier(bad,bad[:,:2],bad,bad,bad)
        with self.assertRaises(ValueError):
            masked_change_brier(bad,bad,bad,bad,bad,strength=9)
        x=np.zeros((28,7,32,32),dtype=np.float32)
        with self.assertRaises(ValueError):
            History({"x":x},[12],4,np.zeros(6),np.ones(6),augment=True,water_margin=.2)

if __name__=="__main__":unittest.main()
