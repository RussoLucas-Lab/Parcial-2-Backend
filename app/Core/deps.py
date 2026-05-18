# ─── Dependencies ──────────────────────────────────────────────────────────────────

# Manejo de dependencias, donde se conecta JWT, usuarios, permisso, rutas protegidas, autorizacion por roles, etc. Las dependencias son funciones que se ejecutan antes de la función de ruta, y pueden recibir parámetros (como el token) y devolver valores (como el usuario autenticado). Si una dependencia lanza una excepción, la ejecución se detiene y se devuelve un error al cliente.

#Flujo
#  → extraer token
#  → validar token
#  → buscar usuario
#  → verificar que esté activo
#  → verificar permisos

# ───────────────────────────────────────────────────────────────────────────────────

from typing import Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

from app.Core.security import decode_access_token
from app.Core.unit_of_work import UnitOfWork, get_uow
from app.model.Usuario.model import Usuario
from app.model.Usuario.model import UsuarioPublic

# Definición de la dependencia para extraer el token de autenticación, busca en el header "Authorization: Bearer token"

# El tokenUrl es la ruta donde se obtiene el token, en este caso "/api/v1/auth/token", que es la ruta de autenticación. Esta dependencia se usará en las rutas protegidas para obtener el token del cliente y luego validar el token para obtener el usuario autenticado.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/token"
)

# ───Dependencia principal ───────────────────────────────────────────────────────────
# Obtiene el usuario actual a partir del token de autenticación. Esta función decodifica el token, verifica su validez y busca el usuario correspondiente en la base de datos. Si el token es inválido o el usuario no existe, se lanza una excepción HTTP 401 Unauthorized.   
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> Usuario:
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    username: str | None = payload.get("sub")
    if username is None:
        raise credentials_exception

    with uow:
        user = uow.usuarios.get_by_username(username)

    if user is None:
        raise credentials_exception

    return user
# ───────────────────────────────────────────────────────────────────────────────────

# ───Usuario Activo ───────────────────────────────────────────────────────────
# Verifica que el usuario autenticado esté activo. Si el usuario está desactivado, se lanza una excepción HTTP 400 Bad Request. Esta función se puede usar como dependencia adicional en las rutas protegidas para asegurarse de que solo los usuarios activos puedan acceder a ellas.
async def get_current_active_user(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> Usuario:
    
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario desactivada",
        )
    return current_user
# ───────────────────────────────────────────────────────────────────────────────────

# ───Role Based Access Control. (RBAC) ──────────────────────────────────────────────

# Esta función es una fábrica de dependencias que genera un verificador de roles basado en una lista de roles permitidos. El verificador de roles se puede usar como dependencia en las rutas protegidas para controlar el acceso según el rol del usuario autenticado. Si el rol del usuario no está en la lista de roles permitidos, se lanza una excepción HTTP 403 Forbidden.
def require_role(allowed_roles: list[str]):
    async def role_checker(
        current_user: Annotated[Usuario, Depends(get_current_active_user)],
    ) -> Usuario:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permisos insuficientes. Tu rol es '{current_user.role}'. "
                    f"Se requiere uno de: {allowed_roles}"
                ),
            )
        return current_user

    return role_checker

# ───────────────────────────────────────────────────────────────────────────────────

# ───Role Based Access Control. (RBAC) ──────────────────────────────────────────────
# Esta clase extiende OAuth2PasswordBearer para extraer el token de autenticación exclusivamente de una cookie HttpOnly llamada "access_token". El soporte para el header Authorization fue deshabilitado para maximizar la seguridad y forzar el uso de cookies HttpOnly, que no pueden ser leídas por JavaScript (mitigando ataques XSS). Si no se encuentra el token en la cookie, se lanza una excepción HTTP 401 Unauthorized.

class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> str | None:
        
        token = request.cookies.get("access_token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No autenticado",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="/api/v1/auth/token")

# ───────────────────────────────────────────────────────────────────────────────────
