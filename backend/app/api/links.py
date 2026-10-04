from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.session import get_db
from app.models.entities import Vm, Server, VmServerLink
from app.core.deps import get_current_user, require_role

router = APIRouter(prefix="/api/links", tags=["links"])

class LinkIn(BaseModel):
    vm_id: str
    server_id: str

@router.get("")
def lista(db: Session = Depends(get_db), _=Depends(get_current_user)):
    out = []
    for vm_id, server_id, method, conf, manual in db.query(
            VmServerLink.vm_id, VmServerLink.server_id, VmServerLink.match_method,
            VmServerLink.confidence, VmServerLink.manual_override).all():
        out.append({"vm_id": str(vm_id), "server_id": str(server_id),
                    "method": method, "confidence": conf, "manual": manual})
    return out

@router.post("")
def crear(body: LinkIn, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    if not db.query(Vm).filter(Vm.id == body.vm_id).first():
        raise HTTPException(404, "VM no encontrada")
    if not db.query(Server).filter(Server.id == body.server_id).first():
        raise HTTPException(404, "Servidor no encontrado")
    row = db.query(VmServerLink).filter(VmServerLink.vm_id == body.vm_id).first()
    if row:
        row.server_id = body.server_id
        row.match_method = "manual"
        row.confidence = 100
        row.manual_override = True
    else:
        db.add(VmServerLink(vm_id=body.vm_id, server_id=body.server_id,
                            match_method="manual", confidence=100, manual_override=True))
    db.commit()
    return {"ok": True}

@router.delete("/{vm_id}")
def eliminar(vm_id: str, db: Session = Depends(get_db), _=Depends(require_role("admin", "operator"))):
    row = db.query(VmServerLink).filter(VmServerLink.vm_id == vm_id).first()
    if not row:
        raise HTTPException(404, "Link no encontrado")
    db.delete(row)
    db.commit()
    return {"ok": True}
