from typing import Callable, Literal, Tuple

from PIL.Image import Image as ImageType
from torch import Tensor
from torch.nn import Module

DreamSimType = Literal[
    "ensemble",
    "dino_vitb16",
    "clip_vitb32",
    "open_clip_vitb32",
    "dinov2_vitb14",
    "synclr_vitb16",
]


class PerceptualModel(Module):
    device: str

    def __call__(self, img_a: Tensor, img_b: Tensor) -> Tensor: ...
    def forward(self, img_a: Tensor, img_b: Tensor) -> Tensor: ...
    def embed(self, img: Tensor) -> Tensor: ...


def dreamsim(
    pretrained: bool = ...,
    device: str = ...,
    cache_dir: str = ...,
    normalize_embeds: bool = ...,
    dreamsim_type: DreamSimType = ...,
    use_patch_model: bool = ...,
) -> Tuple[PerceptualModel, Callable[[ImageType], Tensor]]: ...
