# pyright: standard

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from ..utils.common import compute_file_hash, farthest_point_sampling
from ..utils.console import log_info, log_warn
from ..utils.feature import get_image_features_use_cache
from ..utils.image import IMG_EXTS
from .cache import CacheName
from .connection import get_connection


class ImageRepo:
    def __init__(self, repo_name: str | None = None):
        self.ccip_features: NDArray[np.float32] | None = None
        self.dreamsim_features: NDArray[np.float32] | None = None
        self.hashes: List[bytes] = []
        self.labels: List[str] = []

        self._repo_name: str | None = None
        self._repo_id: int | None = None
        self.repo_path: Path | None = None

        if repo_name is not None:
            self.load(repo_name)

    @property
    def size(self) -> int:
        return len(self.hashes)

    @property
    def repo_name(self) -> str | None:
        return self._repo_name

    @repo_name.setter
    def repo_name(self, name: str) -> None:
        self._repo_name = name

    def _resolve_repo_id(self) -> int:
        conn = get_connection()
        row = conn.execute(
            """SELECT repo_id FROM repos WHERE name = ?""",
            (self._repo_name,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Repository '{self._repo_name}' not found")
        return row[0]

    def load(self, repo_name: str) -> bool:
        """加载仓库元数据与 hash/label 索引（不读取特征 BLOB）"""
        self._repo_name = repo_name
        conn = get_connection()

        row = conn.execute(
            """SELECT repo_id, path FROM repos WHERE name = ?""",
            (repo_name,),
        ).fetchone()
        if row is None:
            log_warn(f"无效的仓库：{repo_name}")
            self.ccip_features = None
            self.dreamsim_features = None
            self.hashes = []
            self.labels = []
            self.repo_path = None
            self._repo_id = None
            return False

        self._repo_id = row[0]
        self.repo_path = Path(row[1])

        rows = conn.execute(
            """SELECT hash, label FROM images
               WHERE repo_id = ? ORDER BY rowid""",
            (self._repo_id,),
        ).fetchall()

        self.hashes = [r[0] for r in rows]
        self.labels = [r[1] for r in rows]
        self.ccip_features = None
        self.dreamsim_features = None

        return True

    def load_features(self, ccip: bool = False, dreamsim: bool = False) -> None:
        """按需加载特征向量，过滤为拥有所请求特征的子集，hashes/labels 同步收窄"""
        assert self._repo_id is not None
        if not ccip and not dreamsim:
            return

        conn = get_connection()

        if ccip:
            rows = conn.execute(
                """SELECT hash, label, ccip_feature FROM images
                   WHERE repo_id = ? AND ccip_feature IS NOT NULL
                   ORDER BY rowid""",
                (self._repo_id,),
            ).fetchall()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.ccip_features = np.stack([np.frombuffer(r[2], dtype=np.float32) for r in rows]) if rows else None

        if dreamsim:
            rows = conn.execute(
                """SELECT hash, label, dreamsim_feature FROM images
                   WHERE repo_id = ? AND dreamsim_feature IS NOT NULL
                   ORDER BY rowid""",
                (self._repo_id,),
            ).fetchall()
            self.hashes = [r[0] for r in rows]
            self.labels = [r[1] for r in rows]
            self.dreamsim_features = np.stack([np.frombuffer(r[2], dtype=np.float32) for r in rows]) if rows else None

    def feature_status(self) -> Tuple[int, int, int]:
        """轻量查询特征覆盖状态，返回 (total, ccip_count, dreamsim_count)"""
        assert self._repo_id is not None
        conn = get_connection()
        row = conn.execute(
            """SELECT COUNT(*), COUNT(ccip_feature), COUNT(dreamsim_feature)
               FROM images WHERE repo_id = ?""",
            (self._repo_id,),
        ).fetchone()
        return row[0], row[1], row[2]

    def save(self) -> None:
        assert self._repo_name is not None, "repo_name 未设置，无法保存"
        assert self.repo_path is not None, "repo_path 未设置，无法保存"

        conn = get_connection()
        with conn:
            conn.execute(
                """INSERT INTO repos (name, path) VALUES (?, ?)
                   ON CONFLICT(name) DO UPDATE SET path = excluded.path""",
                (self._repo_name, str(self.repo_path)),
            )
            repo_id: int = conn.execute(
                """SELECT repo_id FROM repos WHERE name = ?""",
                (self._repo_name,),
            ).fetchone()[0]
            self._repo_id = repo_id

            conn.executemany(
                """INSERT INTO images (repo_id, hash, label, ccip_feature, dreamsim_feature)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(repo_id, hash) DO UPDATE SET
                       label = excluded.label,
                       ccip_feature = COALESCE(excluded.ccip_feature, images.ccip_feature),
                       dreamsim_feature = COALESCE(excluded.dreamsim_feature, images.dreamsim_feature)""",
                [
                    (
                        repo_id,
                        h,
                        label,
                        self.ccip_features[i].tobytes() if self.ccip_features is not None else None,
                        self.dreamsim_features[i].tobytes() if self.dreamsim_features is not None else None,
                    )
                    for i, (h, label) in enumerate(zip(self.hashes, self.labels))
                ],
            )

    def sample(self, max_num: int) -> None:
        """
        从每个类别中随机采样最多 max_num 个样本，用于分类参考。
        会就地覆盖 features / hashes / labels。
        """
        assert self.ccip_features is not None
        assert len(self.ccip_features) == len(self.labels) == len(self.hashes)

        # 按 label 分组索引
        label_to_indices: Dict[str, List[int]] = defaultdict(list)
        for idx, label in enumerate(self.labels):
            label_to_indices[label].append(idx)

        # 每个类别随机采样
        selected_indices: List[int] = []
        for label, indices in label_to_indices.items():
            if len(indices) <= max_num:
                selected_indices.extend(indices)
            else:
                from imgutils.metrics import ccip_batch_differences

                distance_matrix = ccip_batch_differences([self.ccip_features[i, :] for i in indices])
                sample_indices_local = farthest_point_sampling(distance_matrix, max_num)
                sample_indices = [indices[i] for i in sample_indices_local]

                selected_indices.extend(sample_indices)

        # 同步裁剪所有成员变量
        self.ccip_features = self.ccip_features[selected_indices, :]
        if self.dreamsim_features is not None:
            self.dreamsim_features = self.dreamsim_features[selected_indices, :]
        self.labels = [self.labels[i] for i in selected_indices]
        self.hashes = [self.hashes[i] for i in selected_indices]

    @staticmethod
    def scan_imgs_with_label(repo_path: Path) -> Tuple[List[Path], List[str]]:
        exts = IMG_EXTS
        image_paths: List[Path] = []
        labels: List[str] = []

        for category_dir in repo_path.iterdir():
            if not category_dir.is_dir():
                continue

            label = category_dir.name
            for ext in exts:
                for img_path in category_dir.rglob(ext):
                    image_paths.append(img_path)
                    labels.append(label)

        return image_paths, labels

    def purge(self, name: str) -> bool:
        """移除索引中已经不存在于磁盘的图片记录"""
        self.load(name)
        assert self.repo_path is not None
        assert self._repo_id is not None

        image_paths, _ = self.scan_imgs_with_label(self.repo_path)
        existing_hashes: Set[bytes] = set()

        for p in tqdm(image_paths, desc="计算现有文件哈希"):
            h = compute_file_hash(p)
            existing_hashes.add(h)

        conn = get_connection()
        with conn:
            # 先查出要删除的数量
            before_count = conn.execute(
                """SELECT COUNT(*) FROM images WHERE repo_id = ?""",
                (self._repo_id,),
            ).fetchone()[0]

            if not existing_hashes:
                conn.execute(
                    """DELETE FROM images WHERE repo_id = ?""",
                    (self._repo_id,),
                )
            else:
                # 用临时表存放现有 hash 集合
                conn.execute("""CREATE TEMP TABLE IF NOT EXISTS _existing_hashes
                       (hash BLOB PRIMARY KEY)""")
                conn.execute("""DELETE FROM _existing_hashes""")
                conn.executemany(
                    """INSERT OR IGNORE INTO _existing_hashes (hash) VALUES (?)""",
                    [(h,) for h in existing_hashes],
                )
                conn.execute(
                    """DELETE FROM images
                       WHERE repo_id = ? AND hash NOT IN
                           (SELECT hash FROM _existing_hashes)""",
                    (self._repo_id,),
                )
                conn.execute("""DROP TABLE IF EXISTS _existing_hashes""")

            after_count = conn.execute(
                """SELECT COUNT(*) FROM images WHERE repo_id = ?""",
                (self._repo_id,),
            ).fetchone()[0]

        removed = before_count - after_count
        if removed == 0:
            log_info("No images to purge.")
            return False

        log_info(f"Purged {removed} images from repository '{name}'.")
        return True

    def update(self, name: str, extract_ccip: bool = False, extract_dreamsim: bool = False) -> bool:
        """更新仓库索引，按需提取特征"""
        self.load(name)
        assert self.repo_path is not None
        assert self._repo_id is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        hash_to_index: Dict[bytes, int] = {h: i for i, h in enumerate(self.hashes)}
        hash_to_path: Dict[bytes, Path] = {}
        updated_labels = 0
        new_entries: List[Tuple[bytes, str]] = []
        label_updates: List[Tuple[str, bytes]] = []

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="扫描并同步索引"):
            h = compute_file_hash(p)
            hash_to_path[h] = p

            if h in hash_to_index:  # 已存在索引中
                idx = hash_to_index[h]
                if self.labels[idx] != label:  # 分类发生变化，仅更新 label
                    label_updates.append((label, h))
                    updated_labels += 1
            else:  # 新图片
                new_entries.append((h, label))

        conn = get_connection()

        # 同步 hash 和 label
        with conn:
            if label_updates:
                conn.executemany(
                    """UPDATE images SET label = ?
                       WHERE repo_id = ? AND hash = ?""",
                    [(label, self._repo_id, h) for label, h in label_updates],
                )
            if new_entries:
                conn.executemany(
                    """INSERT INTO images (repo_id, hash, label)
                       VALUES (?, ?, ?)""",
                    [(self._repo_id, h, label) for h, label in new_entries],
                )

        if new_entries or updated_labels:
            log_info(f"增加了 {len(new_entries)} 张新图片，更新了 {updated_labels} 个标签。")

        # 按需提取特征
        if extract_ccip:
            self._extract_missing_feature("ccip", hash_to_path)
        if extract_dreamsim:
            self._extract_missing_feature("dreamsim", hash_to_path)

        return len(new_entries) > 0 or updated_labels > 0 or extract_ccip or extract_dreamsim

    def deduplicate(self, name: str) -> bool:
        """基于文件hash去重仓库中的重复图片，如果标签与记录不符输出提示手动处理"""
        self.load(name)
        assert self.repo_path is not None

        image_paths, labels = self.scan_imgs_with_label(self.repo_path)

        @dataclass
        class HashIndexInfo:
            label: str
            hit: int = 0

        hash_index: Dict[bytes, HashIndexInfo] = {
            h: HashIndexInfo(label=self.labels[i]) for i, h in enumerate(self.hashes)
        }

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="扫描并同步索引"):
            h = compute_file_hash(p)

            if h in hash_index:
                index_info = hash_index[h]

                if index_info.label != label:
                    log_info(
                        f"发现与数据库存储标签不符的图片[green]",
                        f"{index_info.label}[/green]!=[red]{label}[/red]",
                        f"：[orchid]{p}[/orchid]",
                        sep="",
                    )
                    continue

                index_info.hit += 1

                if index_info.hit > 1:
                    p.unlink()
                    log_info(f"删除重复图片: [orchid]{p}[/orchid]")

        return True

    def scan_init(self, repo_name: str, path: Path, extract_ccip: bool = False, extract_dreamsim: bool = False) -> bool:
        """初始化扫描一个已分类仓库"""
        image_paths, labels = self.scan_imgs_with_label(path)

        if len(image_paths) == 0:
            log_warn("未发现图片，初始化失败")
            return False

        hashes: List[bytes] = []
        valid_paths: List[Path] = []
        valid_labels: List[str] = []
        seen: Dict[bytes, Tuple[Path, str]] = {}

        for p, label in tqdm(zip(image_paths, labels), total=len(image_paths), desc="计算文件哈希"):
            h = compute_file_hash(p)
            if h in seen:
                prev_path, prev_label = seen[h]
                if prev_label != label:
                    log_warn(
                        f"hash 相同但标签不同: [orchid]{prev_path}[/orchid]([green]{prev_label}[/green])"
                        f" vs [orchid]{p}[/orchid]([red]{label}[/red])，保留前者"
                    )
                continue
            seen[h] = (p, label)
            hashes.append(h)
            valid_paths.append(p)
            valid_labels.append(label)

        if not valid_paths:
            return False

        if extract_ccip:
            ccip_feats, _ = get_image_features_use_cache("ccip", paths_and_hashes=(valid_paths, hashes))
            self.ccip_features = np.stack(ccip_feats, axis=0)
        else:
            self.ccip_features = None

        if extract_dreamsim:
            ds_feats, _ = get_image_features_use_cache("dreamsim", paths_and_hashes=(valid_paths, hashes))
            self.dreamsim_features = np.stack(ds_feats, axis=0)
        else:
            self.dreamsim_features = None

        self.repo_name = repo_name
        self.repo_path = path
        self.hashes = hashes
        self.labels = valid_labels

        return True

    def _extract_missing_feature(self, feature_name: CacheName, hash_to_path: Dict[bytes, Path]) -> None:
        """为仓库中缺失指定特征的图片提取并更新特征"""
        assert self._repo_id is not None
        column = {"ccip": "ccip_feature", "dreamsim": "dreamsim_feature"}[feature_name]
        conn = get_connection()

        missing = conn.execute(
            f"""SELECT hash FROM images
                WHERE repo_id = ? AND {column} IS NULL""",
            (self._repo_id,),
        ).fetchall()

        if not missing:
            log_info(f"所有图片已有 {feature_name} 特征。")
            return

        missing_hashes: List[bytes] = []
        missing_paths: List[Path] = []
        for (h,) in missing:
            if h in hash_to_path:
                missing_hashes.append(h)
                missing_paths.append(hash_to_path[h])

        if not missing_paths:
            log_warn(f"有 {len(missing)} 张图片缺少 {feature_name} 特征，但文件已不存在于磁盘。")
            return

        features, _ = get_image_features_use_cache(feature_name, paths_and_hashes=(missing_paths, missing_hashes))

        with conn:
            conn.executemany(
                f"""UPDATE images SET {column} = ?
                    WHERE repo_id = ? AND hash = ?""",
                [(f.tobytes(), self._repo_id, h) for f, h in zip(features, missing_hashes)],
            )

        log_info(f"提取了 {len(missing_hashes)} 张图片的 {feature_name} 特征。")
