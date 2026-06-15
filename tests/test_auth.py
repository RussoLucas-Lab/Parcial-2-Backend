# =============================================================================
# test_auth.py — Tests de integración: autenticación
# =============================================================================
#
# Endpoints cubiertos:
#   POST /api/v1/auth/register  → registro de usuario
#   POST /api/v1/auth/login     → login con email/password (cookies HTTPOnly)
#   POST /api/v1/auth/logout    → revocación de refresh token
#   GET  /api/v1/auth/me        → perfil del usuario autenticado
#
# Notas de implementación:
#   - Los tokens viajan EXCLUSIVAMENTE en cookies HTTPOnly (no en body).
#   - El body del login devuelve solo `expires_in` (SessionResponse).
#
# =============================================================================

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.conftest import _create_user, _do_login, _seed_base_data


# =============================================================================
# REGISTRO
# =============================================================================

class TestRegister:

    def test_register_ok(self, client: TestClient, seed_data):
        """Usuario nuevo se registra correctamente y recibe rol CLIENT."""
        # Arrange
        payload = {
            "nombre": "Lucas",
            "apellido": "Russo",
            "email": "lucas@example.com",
            "password": "Secure1234!",
        }

        # Act
        resp = client.post("/api/v1/auth/register", json=payload)

        # Assert
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == payload["email"]
        assert data["nombre"] == payload["nombre"]
        assert data["apellido"] == payload["apellido"]
        assert "CLIENT" in data["roles"]
        assert "id" in data
        assert data["activo"] is True

    def test_register_duplicado_retorna_409(self, client: TestClient, db_session: Session, seed_data):
        """Registrar el mismo email dos veces devuelve 409 Conflict."""
        # Arrange
        payload = {
            "nombre": "Lucas",
            "apellido": "Russo",
            "email": "duplicado@example.com",
            "password": "Secure1234!",
        }
        client.post("/api/v1/auth/register", json=payload)

        # Act
        resp = client.post("/api/v1/auth/register", json=payload)

        # Assert
        assert resp.status_code == 409

    def test_register_password_corta_retorna_422(self, client: TestClient, seed_data):
        """Password menor a 8 caracteres devuelve 422 Unprocessable Entity."""
        payload = {
            "nombre": "Test",
            "apellido": "User",
            "email": "short@example.com",
            "password": "123",
        }
        resp = client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 422


# =============================================================================
# LOGIN
# =============================================================================

class TestLogin:

    def test_login_ok(self, client: TestClient, db_session: Session, seed_data):
        """
        Login correcto devuelve 200 con expires_in en body
        y setea access_token + refresh_token como cookies.
        """
        # Arrange
        email, password = "logintest@example.com", "Login1234!"
        _create_user(db_session, email, password, ["CLIENT"])

        # Act
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )

        # Assert
        assert resp.status_code == 200

        body = resp.json()
        assert "expires_in" in body
        assert isinstance(body["expires_in"], int)
        assert body["expires_in"] > 0

        # Los tokens viajan en cookies HTTPOnly
        assert "access_token" in resp.cookies or "access_token" in client.cookies
        assert "refresh_token" in resp.cookies or "refresh_token" in client.cookies

    def test_login_credenciales_invalidas_retorna_401(
        self, client: TestClient, db_session: Session, seed_data
    ):
        """Login con password incorrecta devuelve 401 Unauthorized."""
        # Arrange
        email = "wrongpass@example.com"
        _create_user(db_session, email, "CorrectPass1!", ["CLIENT"])

        # Act
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass!"},
        )

        # Assert
        assert resp.status_code == 401

    def test_login_email_inexistente_retorna_401(self, client: TestClient, seed_data):
        """Login con email no registrado devuelve 401."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "noexiste@example.com", "password": "Whatever1!"},
        )
        assert resp.status_code == 401

    def test_login_campos_faltantes_retorna_422(self, client: TestClient, seed_data):
        """Login sin password devuelve 422."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com"},
        )
        assert resp.status_code == 422


# =============================================================================
# LOGOUT
# =============================================================================

class TestLogout:

    def test_logout_revoca_token(
        self, client: TestClient, db_session: Session, seed_data
    ):
        """
        Logout revoca el refresh token y borra las cookies.
        Acceso posterior al endpoint protegido debe ser rechazado.
        """
        # Arrange: crear usuario y hacer login
        email, password = "logout_test@example.com", "Logout1234!"
        _create_user(db_session, email, password, ["CLIENT"])
        _do_login(client, email, password)

        # Verificar que con la cookie activa se puede acceder a /me
        me_before = client.get("/api/v1/auth/me")
        assert me_before.status_code == 200

        # Act: logout
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 204

        # Assert: después de logout, el endpoint protegido debe rechazar
        # (el access_token ya no está en las cookies o fue invalidado)
        me_after = client.get("/api/v1/auth/me")
        assert me_after.status_code == 401

    def test_logout_sin_sesion_no_rompe(self, client: TestClient, seed_data):
        """Hacer logout sin estar autenticado devuelve 204 (idempotente)."""
        resp = client.post("/api/v1/auth/logout")
        # El endpoint acepta el logout aunque no haya cookie activa
        assert resp.status_code == 204


# =============================================================================
# RATE LIMIT
# =============================================================================

@pytest.mark.skip(
    reason="Rate limiting no está implementado en el proyecto actual. "
           "Agregar middleware de rate limit (ej: slowapi) y quitar este skip."
)
def test_rate_limit(client: TestClient, seed_data):
    """
    Múltiples requests de login en rápida sucesión deben retornar 429.
    Requiere implementar rate limiting middleware.
    """
    email, password = "ratelimit@example.com", "Rate1234!"

    responses = [
        client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        for _ in range(20)
    ]

    status_codes = [r.status_code for r in responses]
    assert 429 in status_codes, (
        "Se esperaba al menos un 429 Too Many Requests después de múltiples "
        f"intentos de login. Códigos recibidos: {set(status_codes)}"
    )


# =============================================================================
# ENDPOINT /me
# =============================================================================

class TestMe:

    def test_me_retorna_perfil_autenticado(
        self, client: TestClient, db_session: Session, seed_data
    ):
        """GET /auth/me con token válido retorna el perfil del usuario."""
        # Arrange
        email, password = "me_test@example.com", "MeTest1234!"
        _create_user(db_session, email, password, ["CLIENT"])
        _do_login(client, email, password)

        # Act
        resp = client.get("/api/v1/auth/me")

        # Assert
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == email
        assert "CLIENT" in data["roles"]

    def test_me_sin_autenticacion_retorna_401(self, client: TestClient, seed_data):
        """GET /auth/me sin cookie devuelve 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
