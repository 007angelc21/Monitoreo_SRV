import enum, uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, BigInteger, Text, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

def uid():
    return uuid.uuid4()

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(20), unique=True)  # admin|operator|viewer

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    role: Mapped[Role] = relationship()

class Vcenter(Base):
    __tablename__ = "vcenters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    hostname: Mapped[str] = mapped_column(String(255))
    port: Mapped[int] = mapped_column(Integer, default=443)
    username: Mapped[str] = mapped_column(String(255))
    password_encrypted: Mapped[str] = mapped_column(Text)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    ca_bundle: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown")  # ok|error|unknown
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)

class Datacenter(Base):
    __tablename__ = "datacenters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    vcenter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcenters.id", ondelete="CASCADE"))
    moref: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    __table_args__ = (UniqueConstraint("vcenter_id", "moref"),)

class Cluster(Base):
    __tablename__ = "clusters"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    datacenter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datacenters.id", ondelete="CASCADE"))
    moref: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))

class Host(Base):
    __tablename__ = "hosts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    cluster_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True)
    vcenter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcenters.id", ondelete="CASCADE"))
    moref: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    connection_state: Mapped[str] = mapped_column(String(30), default="unknown")
    power_state: Mapped[str] = mapped_column(String(30), default="unknown")
    cpu_mhz_total: Mapped[int] = mapped_column(Integer, default=0)
    mem_bytes_total: Mapped[int] = mapped_column(BigInteger, default=0)
    cpu_used_mhz: Mapped[int] = mapped_column(Integer, default=0)
    mem_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

class Server(Base):
    __tablename__ = "servers"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    hostname: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    system_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    primary_ip: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    agent_status: Mapped[str] = mapped_column(String(20), default="unknown")
    last_scrape_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class Vm(Base):
    __tablename__ = "vms"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    vcenter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcenters.id", ondelete="CASCADE"))
    host_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("hosts.id", ondelete="SET NULL"), nullable=True)
    datacenter_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("datacenters.id", ondelete="SET NULL"), nullable=True)
    moref: Mapped[str] = mapped_column(String(50))
    instance_uuid: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    guest_hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    guest_os: Mapped[str | None] = mapped_column(String(255), nullable=True)
    power_state: Mapped[str] = mapped_column(String(20), default="unknown")
    cpu_count: Mapped[int] = mapped_column(Integer, default=0)
    mem_mb: Mapped[int] = mapped_column(Integer, default=0)
    ips: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    macs: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    tools_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    snapshot_count: Mapped[int] = mapped_column(Integer, default=0)
    oldest_snapshot_days: Mapped[int] = mapped_column(Integer, default=0)

class Datastore(Base):
    __tablename__ = "datastores"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    vcenter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vcenters.id", ondelete="CASCADE"))
    moref: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capacity_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    free_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

class VmServerLink(Base):
    __tablename__ = "vm_server_links"
    vm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vms.id", ondelete="CASCADE"), primary_key=True)
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), primary_key=True)
    match_method: Mapped[str] = mapped_column(String(30))
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    manual_override: Mapped[bool] = mapped_column(Boolean, default=False)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    metric: Mapped[str] = mapped_column(String(255))
    warn_threshold: Mapped[float | None] = mapped_column(nullable=True)
    crit_threshold: Mapped[float | None] = mapped_column(nullable=True)
    duration: Mapped[str] = mapped_column(String(20), default="5m")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True)
    scope_type: Mapped[str] = mapped_column(String(20))
    scope_id: Mapped[str] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(20))  # INFO|WARNING|CRITICAL
    status: Mapped[str] = mapped_column(String(20), default="firing")
    value: Mapped[float | None] = mapped_column(nullable=True)
    threshold: Mapped[float | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dedup_count: Mapped[int] = mapped_column(Integer, default=1)

class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"))
    channel: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    resource: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class MetricSample(Base):
    """Histórico en PG (downsample 5 min). Prometheus = tiempo real,
    PG = respaldo histórico y rangos largos si Prometheus falla."""
    __tablename__ = "metric_samples"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    metric: Mapped[str] = mapped_column(String(30), index=True)  # cpu|ram|disk|load1|net_rx|net_tx
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column()

class AuthLog(Base):
    __tablename__ = "auth_logs"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String(255), index=True)
    success: Mapped[bool] = mapped_column(Boolean)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class NetworkInterface(Base):
    __tablename__ = "network_interfaces"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    mac: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ips: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    operstate: Mapped[str] = mapped_column(String(20), default="unknown")
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class ServiceStatus(Base):
    __tablename__ = "services"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uid)
    server_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    systemd_unit: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unknown")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    last_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
