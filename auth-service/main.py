"""
Auth Service — JWT Token Generation

Registers itself in Consul for Traefik discovery.
Provides a login endpoint that returns signed JWT tokens.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import datetime
import consul
import threading
import time

app = FastAPI(title="Auth Service", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Configuration ──────────────────────────────────────────────
SECRET_KEY = "math_solver_academic_secret_key_2026"
ALGORITHM = "HS256"
TOKEN_EXPIRY_HOURS = 4

# Demo users (in a real app, this would be a database)
USERS_DB = {
    "etudiant": "projet",
    "admin": "admin123",
    "demo": "demo",
}


# ── Consul Registration ───────────────────────────────────────
def register_to_consul():
    """Register this service in Consul with Traefik routing tags."""
    max_retries = 10
    for attempt in range(max_retries):
        try:
            c = consul.Consul(host='consul', port=8500)
            c.agent.service.register(
                name='auth-service',
                service_id='auth-service-1',
                address='auth-service',
                port=8001,
                tags=[
                    "traefik.enable=true",
                    "traefik.http.routers.auth.rule=PathPrefix(`/api/auth`)",
                    "traefik.http.routers.auth.entrypoints=web",
                    "traefik.http.services.auth-service.loadbalancer.server.port=8001",
                ]
            )
            print("✅ Auth-Service registered in Consul")
            return
        except Exception as e:
            print(f"⏳ Consul not ready (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(3)
    print("❌ Failed to register in Consul after all retries")


threading.Thread(target=register_to_consul, daemon=True).start()


# ── Models ─────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = TOKEN_EXPIRY_HOURS * 3600


# ── Endpoints ──────────────────────────────────────────────────
@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """
    Authenticate user and return a JWT token.

    Demo credentials: etudiant / projet
    """
    # Validate credentials
    if req.username not in USERS_DB or USERS_DB[req.username] != req.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Build JWT payload
    now = datetime.datetime.utcnow()
    payload = {
        "sub": req.username,
        "role": "user",
        "iat": now,
        "exp": now + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return TokenResponse(access_token=token)


@app.get("/api/auth/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "auth-service"}
