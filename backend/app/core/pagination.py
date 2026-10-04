"""Paginación y errores uniformes: {total, items} + envelope de error."""
from fastapi import Query
from fastapi.responses import JSONResponse

def page_params(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                order: str = Query("asc", pattern="^(asc|desc)$")):
    return {"skip": skip, "limit": limit, "order": order}

def paged(total: int, items: list) -> dict:
    return {"total": total, "items": items}

def err(code: int, message: str, details: dict | None = None):
    return JSONResponse(status_code=code, content={"error": {"code": code, "message": message, "details": details or {}}})
