"""Preserve the extraction timestamp for each NOAA file import.

Revision ID: d0a9b32c5c91
Revises: 8aeb308616e7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d0a9b32c5c91"
down_revision: Union[str, None] = "8aeb308616e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # NULL pour les imports historiques : leur date de lecture exacte est inconnue.
    op.add_column("imports", sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("imports", "extracted_at")
