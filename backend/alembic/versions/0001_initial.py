"""initial schema: roles, users, vcenters, inventario, servers, links, alertas, auditoria

Revision ID: 0001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(20), unique=True, nullable=False))
    op.create_table("users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("vcenters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), default=443),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("verify_ssl", sa.Boolean(), default=True),
        sa.Column("ca_bundle", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), default="unknown"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.String(50), nullable=True))
    op.create_table("datacenters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vcenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vcenters.id", ondelete="CASCADE")),
        sa.Column("moref", sa.String(50)), sa.Column("name", sa.String(255)),
        sa.UniqueConstraint("vcenter_id", "moref"))
    op.create_table("clusters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("datacenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datacenters.id", ondelete="CASCADE")),
        sa.Column("moref", sa.String(50)), sa.Column("name", sa.String(255)))
    op.create_table("hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cluster_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vcenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vcenters.id", ondelete="CASCADE")),
        sa.Column("moref", sa.String(50)), sa.Column("name", sa.String(255)),
        sa.Column("connection_state", sa.String(30), default="unknown"),
        sa.Column("power_state", sa.String(30), default="unknown"),
        sa.Column("cpu_mhz_total", sa.Integer(), default=0),
        sa.Column("mem_bytes_total", sa.BigInteger(), default=0),
        sa.Column("cpu_used_mhz", sa.Integer(), default=0),
        sa.Column("mem_used_bytes", sa.BigInteger(), default=0))
    op.create_table("servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("hostname", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("system_uuid", sa.String(64), nullable=True, index=True),
        sa.Column("primary_ip", sa.String(45), nullable=True, index=True),
        sa.Column("os", sa.String(100), nullable=True),
        sa.Column("agent_status", sa.String(20), default="unknown"),
        sa.Column("last_scrape_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table("vms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vcenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vcenters.id", ondelete="CASCADE")),
        sa.Column("host_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("datacenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("datacenters.id", ondelete="SET NULL"), nullable=True),
        sa.Column("moref", sa.String(50)),
        sa.Column("instance_uuid", sa.String(64), nullable=True, unique=True, index=True),
        sa.Column("name", sa.String(255), index=True),
        sa.Column("guest_os", sa.String(255), nullable=True),
        sa.Column("power_state", sa.String(20), default="unknown"),
        sa.Column("cpu_count", sa.Integer(), default=0),
        sa.Column("mem_mb", sa.Integer(), default=0),
        sa.Column("ips", postgresql.JSONB(), nullable=True),
        sa.Column("macs", postgresql.JSONB(), nullable=True),
        sa.Column("tools_status", sa.String(40), nullable=True),
        sa.Column("snapshot_count", sa.Integer(), default=0),
        sa.Column("oldest_snapshot_days", sa.Integer(), default=0))
    op.create_table("datastores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vcenter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vcenters.id", ondelete="CASCADE")),
        sa.Column("moref", sa.String(50)), sa.Column("name", sa.String(255)),
        sa.Column("type", sa.String(50), nullable=True),
        sa.Column("capacity_bytes", sa.BigInteger(), default=0),
        sa.Column("free_bytes", sa.BigInteger(), default=0))
    op.create_table("vm_server_links",
        sa.Column("vm_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vms.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("servers.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("match_method", sa.String(30)),
        sa.Column("confidence", sa.Integer(), default=0),
        sa.Column("manual_override", sa.Boolean(), default=False))
    op.create_table("network_interfaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("servers.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(50)), sa.Column("mac", sa.String(20), nullable=True),
        sa.Column("ips", postgresql.JSONB(), nullable=True),
        sa.Column("operstate", sa.String(20), default="unknown"),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True))
    op.create_table("services",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("server_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("servers.id", ondelete="CASCADE"), index=True),
        sa.Column("name", sa.String(100)), sa.Column("systemd_unit", sa.String(150), nullable=True),
        sa.Column("status", sa.String(20), default="unknown"),
        sa.Column("enabled", sa.Boolean(), default=False),
        sa.Column("last_check", sa.DateTime(timezone=True), nullable=True))
    op.create_table("alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("metric", sa.String(255)),
        sa.Column("warn_threshold", sa.Float(), nullable=True),
        sa.Column("crit_threshold", sa.Float(), nullable=True),
        sa.Column("duration", sa.String(20), default="5m"),
        sa.Column("enabled", sa.Boolean(), default=True))
    op.create_table("alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fingerprint", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scope_type", sa.String(20)), sa.Column("scope_id", sa.String(100)),
        sa.Column("severity", sa.String(20)), sa.Column("status", sa.String(20), default="firing"),
        sa.Column("value", sa.Float(), nullable=True), sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedup_count", sa.Integer(), default=1))
    op.create_table("notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alerts.id", ondelete="CASCADE")),
        sa.Column("channel", sa.String(30)), sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table("audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(50)), sa.Column("resource", sa.String(100)),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("auth_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), index=True),
        sa.Column("success", sa.Boolean()),
        sa.Column("ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))

def downgrade():
    for t in ["auth_logs", "audit_logs", "notifications", "alerts", "alert_rules",
              "services", "network_interfaces", "vm_server_links", "datastores",
              "vms", "servers", "hosts", "clusters", "datacenters", "vcenters",
              "users", "roles"]:
        op.drop_table(t)
