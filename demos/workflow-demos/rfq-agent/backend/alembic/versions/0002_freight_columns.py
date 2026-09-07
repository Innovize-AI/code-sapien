"""add rfq_type and freight columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rfq_submissions", sa.Column("rfq_type", sa.String(), nullable=True, server_default="product"), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_origin", sa.Text(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_destination", sa.Text(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_cargo_desc", sa.Text(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_weight_kg", sa.Float(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_volume_cbm", sa.Float(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_truck_type", sa.String(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_distance_km", sa.Float(), nullable=True), schema="rfq")
    op.add_column("rfq_submissions", sa.Column("freight_quote_amount", sa.Float(), nullable=True), schema="rfq")


def downgrade() -> None:
    for col in [
        "freight_quote_amount", "freight_distance_km", "freight_truck_type",
        "freight_volume_cbm", "freight_weight_kg", "freight_cargo_desc",
        "freight_destination", "freight_origin", "rfq_type",
    ]:
        op.drop_column("rfq_submissions", col, schema="rfq")
