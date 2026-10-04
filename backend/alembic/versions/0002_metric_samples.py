"""0002: metric_samples (histórico en PG)."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("metric_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("server_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("servers.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("metric", sa.String(30), index=True, nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), index=True, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.UniqueConstraint("server_id", "metric", "ts", name="uq_sample"))
    op.create_index("ix_samples_lookup", "metric_samples", ["server_id", "metric", "ts"])

def downgrade():
    op.drop_index("ix_samples_lookup", table_name="metric_samples")
    op.drop_table("metric_samples")
