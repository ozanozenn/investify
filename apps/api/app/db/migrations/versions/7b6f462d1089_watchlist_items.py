"""watchlist items (ADR-013)

Revision ID: 7b6f462d1089
Revises: cbb5490621ad
Create Date: 2026-10-27 22:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b6f462d1089"
down_revision: Union[str, None] = "cbb5490621ad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_status", sa.String(length=20), nullable=True),
        sa.Column("last_refresh_trigger", sa.String(length=20), nullable=True),
        sa.Column("last_refresh_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticker", name="uq_watchlist_items_ticker"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
