from sqlmodel import SQLModel


# ── Entrada ───────────────────────────────────────────────────────────────────

class LoginRequest(SQLModel):
    email: str
    password: str


class RefreshRequest(SQLModel):
    refresh_token: str


# ── Salida ────────────────────────────────────────────────────────────────────

class TokenResponse(SQLModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
