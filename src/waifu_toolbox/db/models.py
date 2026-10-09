from dataclasses import dataclass
from pathlib import Path


@dataclass
class ImageInfo:
    relative_path: str
    label: str


@dataclass
class RepoImages:
    repo_path: Path
    images: list[ImageInfo]


@dataclass
class RepoSummary:
    name: str
    path: str


@dataclass
class RepoInfo:
    name: str
    path: str
    total_images: int
    label_count: int
    ccip_count: int
    dreamsim_count: int


@dataclass
class CacheClearResult:
    ccip_deleted: int
    dreamsim_deleted: int
