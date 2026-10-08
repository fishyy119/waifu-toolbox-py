from sqlalchemy import (
    Column,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    PrimaryKeyConstraint,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

repos = Table(
    "repos",
    metadata,
    Column("repo_id", Integer, nullable=False),
    Column("name", Text, nullable=False),
    Column("path", Text, nullable=False),
    PrimaryKeyConstraint("repo_id", name="pk_repos"),
    UniqueConstraint("name", name="uq_repos_name"),
    sqlite_autoincrement=True,
)

images = Table(
    "images",
    metadata,
    Column("repo_id", Integer, nullable=False),
    Column("hash", LargeBinary, nullable=False),
    Column("label", Text, nullable=False),
    Column("ccip_feature", LargeBinary),
    Column("dreamsim_feature", LargeBinary),
    Column("relative_path", Text),
    ForeignKeyConstraint(
        ["repo_id"],
        ["repos.repo_id"],
        name="fk_images_repo_id_repos",
        ondelete="CASCADE",
    ),
    UniqueConstraint("repo_id", "hash", name="uq_images_repo_id"),
)

Index("idx_images_repo", images.c.repo_id)
Index("idx_images_hash", images.c.hash)

feature_cache = Table(
    "feature_cache",
    metadata,
    Column("hash", LargeBinary, nullable=False),
    Column("feature_type", Text, nullable=False),
    Column("feature", LargeBinary, nullable=False),
    PrimaryKeyConstraint("hash", "feature_type", name="pk_feature_cache"),
)
