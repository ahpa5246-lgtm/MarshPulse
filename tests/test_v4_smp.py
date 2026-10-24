"""Genuine upstream SMP model construction and persistence-anchored gradient smoke."""
import sys,unittest
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"ml"))
from mash_plus_smp import SMPPersistenceUnet
from marshnet_v3 import masked_brier_bce

class SMPArchitectureSmoke(unittest.TestCase):
    def test_upstream_unet_real_forward_backward(self):
        net=SMPPersistenceUnet(lookback=4,encoder="resnet18",pretrained=False)
        self.assertEqual(net.config["upstream"],"segmentation_models_pytorch")
        self.assertIsNone(net.config["encoder_weights"])
        x=torch.randn(2,4,7,32,32)
        p=torch.full((2,32,32),.19)
        y=torch.zeros_like(p);y[:,8:12,8:12]=1.
        valid=torch.ones_like(p)
        net.eval()
        with torch.no_grad():
            init=net(x,p).sigmoid()
            self.assertTrue(torch.allclose(init,p,atol=1e-6))
        net.train()
        loss=masked_brier_bce(net(x,p),y,valid,pos_weight=3.)
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        self.assertTrue(torch.isfinite(net.net.segmentation_head[0].weight.grad).all())
    def test_input_shape_enforced(self):
        net=SMPPersistenceUnet(lookback=4,pretrained=False)
        with self.assertRaises(ValueError):
            net(torch.zeros(1,2,7,32,32),torch.full((1,32,32),.5))

if __name__=="__main__":unittest.main()
