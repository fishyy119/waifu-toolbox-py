from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from ...db.models import ImageInfo, RepoInfo
from ..services.library import DirectoryNode

RepoName = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_]+$")]
TaskKind = Literal[
    "repo.create",
    "repo.update",
    "repo.purge",
    "repo.deduplicate",
    "repo.flatten",
    "repo.rename",
    "repo.path",
    "repo.delete",
    "classify.reference",
    "classify.cluster",
    "sort",
    "convert",
    "search",
    "cache.clear",
]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: object | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class RepoCreate(RequestModel):
    kind: Literal["repo.create"]
    repo_name: RepoName
    path: Path
    ccip: bool = False
    dreamsim: bool = False


class RepoAction(RequestModel):
    kind: Literal["repo.update", "repo.purge", "repo.deduplicate", "repo.flatten"]
    repo_name: RepoName
    ccip: bool = False
    dreamsim: bool = False


class RepoRename(RequestModel):
    kind: Literal["repo.rename"]
    repo_name: RepoName
    new_name: RepoName


class RepoPath(RequestModel):
    kind: Literal["repo.path"]
    repo_name: RepoName
    path: Path


class RepoDelete(RequestModel):
    kind: Literal["repo.delete"]
    repo_name: RepoName
    confirmation: str


class ClassifyReference(RequestModel):
    kind: Literal["classify.reference"]
    path: Path
    repo_name: RepoName
    num_references: Annotated[int, Field(ge=5, le=100)] = 20


class ClassifyCluster(RequestModel):
    kind: Literal["classify.cluster"]
    path: Path
    inplace: bool = False


class SortImages(RequestModel):
    kind: Literal["sort"]
    path: Path
    avoid_sorted: bool = True


class ConvertImages(RequestModel):
    kind: Literal["convert"]
    path: Path
    source_format: Literal["bmp", "jpg", "jpeg", "png"] = "bmp"
    replace: bool = False


class SearchImages(RequestModel):
    kind: Literal["search"]
    repo_name: RepoName
    path: Path
    top_k: Annotated[int, Field(ge=1, le=50)] = 10
    skip_update: bool = True


class ClearCache(RequestModel):
    kind: Literal["cache.clear"]
    ccip: bool = False
    dreamsim: bool = False


TaskRequest = Annotated[
    RepoCreate
    | RepoAction
    | RepoRename
    | RepoPath
    | RepoDelete
    | ClassifyReference
    | ClassifyCluster
    | SortImages
    | ConvertImages
    | SearchImages
    | ClearCache,
    Field(discriminator="kind"),
]


class SearchMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    path: str
    label: str
    similarity: float


class TaskResultResponse(BaseModel):
    """任务结果的稳定展示字段，业务结果由 API 统一适配。"""

    details: list[str] = Field(default_factory=list)
    output_path: str | None = None
    counts: dict[str, int] = Field(default_factory=dict)
    search_results: list[SearchMatch] = Field(default_factory=lambda: list[SearchMatch]())


class TaskResponse(BaseModel):
    id: str
    name: str
    kind: TaskKind
    status: Literal["pending", "running", "completed", "failed"]
    progress: float
    progress_desc: str
    progress_text: str
    result_text: str
    error: str
    created_at: datetime
    result: TaskResultResponse | None = None


class LabelCount(BaseModel):
    label: str
    count: int


class RepoDetailResponse(BaseModel):
    info: RepoInfo
    directories: list[DirectoryNode]
    labels: list[LabelCount]


class ImagePageResponse(BaseModel):
    items: list[ImageInfo]
    total: int
    page: int
    page_size: int
