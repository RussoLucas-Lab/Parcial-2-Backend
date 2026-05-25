from fastapi import Depends, HTTPException, Path, status

from app.Core.deps import get_current_user
from app.modules.Usuario.model import Usuario

# Esta función de dependencia se puede usar en cualquier endpoint que tenga un path parameter usuario_id, y se encargará de verificar si el usuario autenticado es el mismo que el usuario_id del path o si tiene rol ADMIN. Si no cumple ninguna de esas condiciones, lanza un HTTP 403 Forbidden.

def require_same_user_or_admin(
    usuario_id: int = Path(...),
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:

    is_admin = any(
        ur.rol_codigo == "ADMIN"
        for ur in current_user.usuario_roles
    )

    is_client = any(
        ur.rol_codigo == "CLIENT"
        for ur in current_user.usuario_roles
    )

    if is_admin:
        return current_user

    if is_client and current_user.id == usuario_id:
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No autorizado",
    )