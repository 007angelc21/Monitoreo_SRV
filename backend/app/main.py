from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from prometheus_client import Counter, Histogram, make_asgi_app
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine
import app.models.entities  # noqa

settings = get_settings()
log = configure_logging(settings.LOG_LEVEL)
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # MVP; prod usa Alembic upgrade head
    log.info("startup complete", db=settings.sqlalchemy_url().split("@")[-1])
    try:
        from app.collectors.scheduler import start
        start()
        log.info("scheduler started")
    except Exception as e:
        log.error("scheduler failed", error=str(e))
    yield
    try:
        from app.collectors.scheduler import stop
        stop()
    except Exception:
        pass

app = FastAPI(title="Monitoreo SRV API", version="1.2.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS.split(","),
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

REQ = Counter("api_requests_total", "requests", ["path", "method", "code"])
LAT = Histogram("api_latency_seconds", "latency", ["path"])

@app.middleware("http")
async def metrics_mw(request, call_next):
    import time
    t = time.time()
    resp = await call_next(request)
    REQ.labels(request.url.path, request.method, resp.status_code).inc()
    LAT.labels(request.url.path).observe(time.time() - t)
    return resp

@app.middleware("http")
async def audit_mw(request: Request, call_next):
    resp = await call_next(request)
    if request.method in ("POST", "PUT", "DELETE") and resp.status_code < 400 \
            and request.url.path.startswith("/api/") and "auth/login" not in request.url.path:
        try:
            from app.db.session import SessionLocal
            from app.core.audit import audit
            from jose import jwt
            uid = None
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer "):
                try:
                    sub = jwt.decode(auth[7:], settings.SECRET_KEY,
                                     algorithms=["HS256"])["sub"]
                    db = SessionLocal()
                    try:
                        from app.models.entities import User
                        u = db.query(User).filter(User.email == sub).first()
                        uid = u.id if u else None
                    finally:
                        db.close()
                except Exception:
                    pass
            db2 = SessionLocal()
            try:
                audit(db2, uid, request.method, request.url.path, None,
                      request.client.host if request.client else None)
            finally:
                db2.close()
        except Exception:
            pass
    return resp

@app.exception_handler(RateLimitExceeded)
async def ratelimit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(429, {"error": {"code": 429, "message": "Rate limit excedido", "details": {}}})

@app.exception_handler(Exception)
async def uniform_errors(request: Request, exc: Exception):
    from fastapi import HTTPException
    if isinstance(exc, HTTPException):
        return JSONResponse(exc.status_code, {"error": {"code": exc.status_code, "message": exc.detail, "details": {}}})
    log.error("unhandled", error=str(exc), path=request.url.path)
    return JSONResponse(500, {"error": {"code": 500, "message": "Error interno", "details": {}}})

from app.api import auth, servers, vcenters, alerts, metrics, links
app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(vcenters.router)
app.include_router(alerts.router)
app.include_router(metrics.router)
app.include_router(links.router)
app.mount("/metrics", make_asgi_app())

@app.get("/")
def root():
    return {"service": "monitoreo-srv", "docs": "/api/docs", "health": "/api/health"}
