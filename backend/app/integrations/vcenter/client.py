"""Cliente vCenter 7: REST (inventario) + SOAP pyVmomi (perf/snapshots/guest).
Compatible vCenter/ESXi 7.0 U1-U3. Maneja auth, cert autofirmado opcional, timeouts y circuit breaker simple."""
import re, ssl, requests
from datetime import datetime, timezone

# Compatibilidad con Python 3.12+: pyVmomi 7.x usa ssl.wrap_socket, que fue removido
# en versiones recientes. Fijamos el alias para que la librería siga funcionando.
if not hasattr(ssl, "wrap_socket"):
    ssl.wrap_socket = ssl.SSLContext.wrap_socket

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class VcenterError(Exception): pass
class VcenterAuthError(VcenterError): pass
class VcenterCertError(VcenterError): pass
class VcenterUnavailable(VcenterError): pass

_circuit: dict[str, dict] = {}  # vcenter_id -> {fails, open_until}

def _cb_check(vcid: str):
    import time
    st = _circuit.get(vcid, {"fails": 0, "open_until": 0})
    if time.time() < st["open_until"]:
        raise VcenterUnavailable("Circuit breaker abierto (vCenter con fallos recientes)")
    return st

def _cb_ok(vcid: str):
    _circuit[vcid] = {"fails": 0, "open_until": 0}

def _cb_fail(vcid: str):
    import time
    st = _circuit.get(vcid, {"fails": 0, "open_until": 0})
    st["fails"] += 1
    if st["fails"] >= 5:
        st["open_until"] = time.time() + 60
    _circuit[vcid] = st

def _ssl_context(verify: bool):
    if verify:
        return ssl.create_default_context()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type((VcenterUnavailable, requests.Timeout)))
def rest_login(host: str, port: int, user: str, password: str, verify: bool, timeout=15) -> str:
    _url = f"https://{host}:{port}/rest/com/vmware/cis/session"
    try:
        r = requests.post(_url, auth=(user, password), verify=verify, timeout=timeout)
    except requests.exceptions.SSLError as e:
        raise VcenterCertError(f"Error TLS con vCenter (usa verify_ssl=false solo si es interno): {e}")
    except (requests.Timeout, requests.ConnectionError) as e:
        raise VcenterUnavailable(f"vCenter no disponible: {e}")
    if r.status_code == 401:
        raise VcenterAuthError("Credenciales vCenter invalidas (401)")
    r.raise_for_status()
    return r.json()["value"]

def rest_list(host, port, sid, path, verify=True, timeout=15):
    r = requests.get(f"https://{host}:{port}/rest{path}", headers={"vmware-api-session-id": sid},
                     verify=verify, timeout=timeout)
    if r.status_code == 401:
        raise VcenterAuthError("Sesion vCenter expirada")
    r.raise_for_status()
    return r.json().get("value", [])

def soap_connect(host, user, password, port=443, verify=True):
    try:
        return SmartConnect(host=host, user=user, pwd=password, port=port, sslContext=_ssl_context(verify))
    except vim.fault.InvalidLogin:
        raise VcenterAuthError("Credenciales SOAP invalidas")
    except ssl.SSLCertVerificationError as e:
        raise VcenterCertError(str(e))
    except Exception as e:
        raise VcenterUnavailable(f"SOAP no disponible: {e}")

def discover_vcenter(vc) -> dict:
    """Descubrimiento completo. vc: objeto Vcenter DB (con password ya descifrado en memoria).
    Retorna dict con datacenters/clusters/hosts/vms/datastores para upsert."""
    from app.core.security import decrypt_secret  # diferido
    vcid = str(vc.id)
    _cb_check(vcid)
    try:
        sid = rest_login(vc.hostname, vc.port, vc.username, decrypt_secret(vc.password_encrypted), vc.verify_ssl)
        dcs = rest_list(vc.hostname, vc.port, sid, "/vcenter/datacenter", vc.verify_ssl)
        clusters = rest_list(vc.hostname, vc.port, sid, "/vcenter/cluster", vc.verify_ssl)
        hosts = rest_list(vc.hostname, vc.port, sid, "/vcenter/host", vc.verify_ssl)
        vms = rest_list(vc.hostname, vc.port, sid, "/vcenter/vm", vc.verify_ssl)
        dss = rest_list(vc.hostname, vc.port, sid, "/vcenter/datastore", vc.verify_ssl)
        si = soap_connect(vc.hostname, vc.username, decrypt_secret(vc.password_encrypted), vc.port, vc.verify_ssl)
        try:
            content = si.RetrieveContent()
            # Enriquecer VMs con guest info + snapshots via SOAP (vCenter 7)
            extra = _enrich_vms_soap(content)
        finally:
            Disconnect(si)
        try:
            requests.delete(f"https://{vc.hostname}:{vc.port}/rest/com/vmware/cis/session",
                            headers={"vmware-api-session-id": sid}, verify=vc.verify_ssl, timeout=10)
        except Exception:
            pass
        _cb_ok(vcid)
        return {"datacenters": dcs, "clusters": clusters, "hosts": hosts, "vms": vms,
                "datastores": dss, "extra": extra}
    except VcenterError:
        _cb_fail(vcid)
        raise

def _enrich_vms_soap(content) -> dict:
    out = {}
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    try:
        for vm in view.view:
            try:
                snaps = []
                def walk(tree, depth=0):
                    for s in (tree or []):
                        snaps.append({"name": s.name, "create": str(s.createTime), "state": s.state})
                        walk(s.childSnapshotList, depth + 1)
                if vm.snapshot:
                    walk(vm.snapshot.rootSnapshotList)
                guest_ips, macs = [], []
                if vm.guest and vm.guest.net:
                    for n in vm.guest.net:
                        if n.ipAddress:
                            guest_ips += [ip for ip in n.ipAddress if ":" not in ip]
                        if n.macAddress:
                            macs.append(n.macAddress)
                out[vm._moId] = {
                    "instance_uuid": vm.config.instanceUuid if vm.config else None,
                    "power": str(vm.runtime.powerState),
                    "cpu": vm.config.hardware.numCPU if vm.config else 0,
                    "mem": vm.config.hardware.memoryMB if vm.config else 0,
                    "guest_os": vm.config.guestFullName if vm.config else None,
                    "hostname": vm.guest.hostName if vm.guest else None,
                    "tools": str(vm.guest.toolsStatus) if vm.guest else None,
                    "ips": guest_ips, "macs": macs, "snapshots": snaps,
                }
            except Exception:
                continue
    finally:
        view.Destroy()
    return out

def _norm_uuid(value) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


def _norm_hostname(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().split(".")[0].strip()


def _norm_ip(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _server_mac_set(server) -> set[str]:
    macs = set()
    for field in ("macs", "network_interfaces"):
        container = getattr(server, field, None)
        if not container:
            continue
        if isinstance(container, (list, tuple, set)):
            items = container
        else:
            items = [container]
        for item in items:
            if hasattr(item, "mac"):
                value = getattr(item, "mac")
                if value:
                    macs.add(re.sub(r"[^a-f0-9]", "", str(value).lower()))
            elif isinstance(item, dict):
                value = item.get("mac") or item.get("macAddress")
                if value:
                    macs.add(re.sub(r"[^a-f0-9]", "", str(value).lower()))
            elif isinstance(item, str):
                macs.add(re.sub(r"[^a-f0-9]", "", item.lower()))
    return macs


def match_vm_to_server(vm_extra: dict, servers: list) -> tuple[str, int] | None:
    """Cascada robusta (no solo nombre):
    1) system_uuid == instanceUuid (100)
    2) hostname Tools == hostname node (90)
    3) MAC overlap (80)
    4) IP exacta unica (70)"""
    if not isinstance(vm_extra, dict):
        return None

    iu = _norm_uuid(vm_extra.get("instance_uuid"))
    if iu:
        for s in servers:
            if _norm_uuid(getattr(s, "system_uuid", None)) == iu:
                return (str(s.id), 100)

    hn = _norm_hostname(vm_extra.get("hostname"))
    if hn:
        for s in servers:
            if _norm_hostname(getattr(s, "hostname", None)) == hn:
                return (str(s.id), 90)

    vmacs = {re.sub(r"[^a-f0-9]", "", str(m).lower()) for m in (vm_extra.get("macs") or []) if m}
    if vmacs:
        for s in servers:
            server_macs = _server_mac_set(s)
            if vmacs & server_macs:
                return (str(s.id), 80)

    vips = {_norm_ip(ip) for ip in (vm_extra.get("ips") or []) if _norm_ip(ip)}
    if vips:
        hits = [s for s in servers if _norm_ip(getattr(s, "primary_ip", None)) in vips]
        if len(hits) == 1:
            return (str(hits[0].id), 70)
    return None
