"""Mash Plus research challenger using the unmodified upstream segmentation-models-pytorch package.

Upstream: https://github.com/qubvel-org/segmentation_models.pytorch
Import optional, installed separately in the V4 notebook; never copy third-party
source into this repository. The zero-initialized correction head starts from
the identical smoothed last-observation baseline as ConvGRU V3.
"""
from __future__ import annotations
import torch
from torch import nn

class SMPPersistenceUnet(nn.Module):
    def __init__(self,lookback=4,encoder="resnet18",pretrained=False,prior_epsilon=.01):
        super().__init__()
        try:
            import segmentation_models_pytorch as smp
        except ImportError as exc:
            raise ImportError("Install the open-source segmentation-models-pytorch package for SMP U-Net") from exc
        if lookback<2 or lookback>12:
            raise ValueError("Lookback must be between 2 and 12")
        if encoder not in ("resnet18","resnet34"):
            raise ValueError("Use a pre-reviewed ResNet18/34 encoder; do not silently change architecture")
        self.lookback=int(lookback)
        self.prior_epsilon=float(prior_epsilon)
        self.net=smp.Unet(encoder_name=encoder,
                          encoder_weights="imagenet" if pretrained else None,
                          in_channels=lookback*7,classes=1,activation=None,
                          encoder_depth=4,decoder_channels=(128,64,32,16))
        # Both competing neural candidates must start with exactly the same
        # persistence prior; training learns only an innovation residual.
        head=self.net.segmentation_head[0]
        nn.init.zeros_(head.weight)
        if head.bias is not None:
            nn.init.zeros_(head.bias)
        self.residual_gain=nn.Parameter(torch.tensor(1.0))
        self.config={"model_name":"Mash Plus","model_version":"V4",
                     "architecture":"SMP_Unet_persistence_residual",
                     "encoder":encoder,"encoder_weights":"imagenet" if pretrained else None,
                     "lookback":self.lookback,
                     "prior_epsilon":self.prior_epsilon,
                     "upstream":"segmentation_models_pytorch"}
    def forward(self,history,prior):
        if history.ndim!=5 or history.shape[1]!=self.lookback or history.shape[2]!=7:
            raise ValueError("Expected [batch,lookback,7,height,width]")
        if prior.shape!=(history.shape[0],history.shape[3],history.shape[4]):
            raise ValueError("Prior grid differs from history grid")
        x=history.reshape(history.shape[0],self.lookback*7,*history.shape[-2:])
        residual=self.net(x)[:,0]
        p=prior.clamp(self.prior_epsilon,1-self.prior_epsilon)
        return torch.logit(p)+self.residual_gain*6*torch.tanh(residual/6)
