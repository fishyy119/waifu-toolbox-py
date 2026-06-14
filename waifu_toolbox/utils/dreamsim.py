from functools import cache
from pathlib import Path
from typing import Callable, NamedTuple, cast

import numpy as np
from numpy.typing import NDArray
from PIL.Image import Image as ImageType
from dreamsim import PerceptualModel, dreamsim
import torch
from torch import Tensor

from ..paths import PATHS
from .image import load_image

DREAMSIM_DEVICE = "cpu"
DREAMSIM_MODEL_TYPE = "synclr_vitb16"
DREAMSIM_MODEL_CACHE_DIR = PATHS.dreamsim_model_root / DREAMSIM_MODEL_TYPE


class DreamSimComponents(NamedTuple):
    model: PerceptualModel
    preprocess: Callable[[ImageType], Tensor]


@cache
def _load_dreamsim_components() -> DreamSimComponents:
    DREAMSIM_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    model, preprocess = dreamsim(
        pretrained=True,
        device=DREAMSIM_DEVICE,
        cache_dir=str(DREAMSIM_MODEL_CACHE_DIR),
        dreamsim_type=DREAMSIM_MODEL_TYPE,
    )
    return DreamSimComponents(model, preprocess)



def normalize_embedding(vector: NDArray[np.float32]) -> NDArray[np.float32]:
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm <= 0:
        raise RuntimeError("DreamSim 生成了无效的 embedding。")
    return vector / norm


def compute_dreamsim_distance_matrix(embeddings: NDArray[np.float32]) -> NDArray[np.float32]:
    distances = np.asarray(1.0 - embeddings @ embeddings.T, dtype=np.float32)
    np.clip(distances, 0.0, 2.0, out=distances)
    np.fill_diagonal(distances, 0.0)
    return distances


def extract_dreamsim_embedding_from_path(img_path: Path) -> NDArray[np.float32]:
    model, preprocess = _load_dreamsim_components()
    image = load_image(img_path, max_size=None, mode="RGB")
    input_tensor = preprocess(image).to(DREAMSIM_DEVICE)

    with torch.no_grad():
        raw_embedding = model.embed(input_tensor)

    embedding_tensor = cast(object, raw_embedding.detach().cpu())
    embedding = np.asarray(embedding_tensor, dtype=np.float32).reshape(-1)
    return normalize_embedding(embedding)
