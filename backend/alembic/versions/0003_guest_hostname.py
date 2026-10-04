"""0003: vms.guest_hostname (hostname reportado por VMware Tools)."""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("vms", sa.Column("guest_hostname", sa.String(255), nullable=True))
    op.create_index("ix_vms_guest_hostname", "vms", ["guest_hostname"])

def downgrade():
    op.drop_index("ix_vms_guest_hostname", table_name="vms")
    op.drop_column("vms", "guest_hostname")
