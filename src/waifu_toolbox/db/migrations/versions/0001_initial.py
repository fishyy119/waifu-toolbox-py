"""创建初始数据库结构。

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "repos",
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("path", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("repo_id", name="pk_repos"),
        sa.UniqueConstraint("name", name="uq_repos_name"),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "images",
        sa.Column("repo_id", sa.Integer(), nullable=False),
        sa.Column("hash", sa.LargeBinary(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("ccip_feature", sa.LargeBinary(), nullable=True),
        sa.Column("dreamsim_feature", sa.LargeBinary(), nullable=True),
        sa.Column("relative_path", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["repo_id"],
            ["repos.repo_id"],
            name="fk_images_repo_id_repos",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("repo_id", "hash", name="uq_images_repo_id"),
    )
    op.create_index("idx_images_hash", "images", ["hash"], unique=False)
    op.create_index("idx_images_repo", "images", ["repo_id"], unique=False)
    op.create_table(
        "feature_cache",
        sa.Column("hash", sa.LargeBinary(), nullable=False),
        sa.Column("feature_type", sa.Text(), nullable=False),
        sa.Column("feature", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("hash", "feature_type", name="pk_feature_cache"),
    )


def downgrade() -> None:
    op.drop_table("feature_cache")
    op.drop_index("idx_images_repo", table_name="images")
    op.drop_index("idx_images_hash", table_name="images")
    op.drop_table("images")
    op.drop_table("repos")
