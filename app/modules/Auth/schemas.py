from sqlmodel import SQLModel


# ── Entrada ───────────────────────────────────────────────────────────────────

class LoginRequest(SQLModel):
    email: str
    password: str


class RefreshRequest(SQLModel):
    refresh_token: str


# ── Salida ────────────────────────────────────────────────────────────────────

class TokenResponse(SQLModel):
    """Uso interno del servicio — los tokens nunca salen en el body."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SessionResponse(SQLModel):
    """Respuesta pública: solo metadata, los tokens viajan en cookies HTTPOnly."""
    expires_in: int
