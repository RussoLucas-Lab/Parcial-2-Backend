# ── Securityy ────────────────────────────────────────────────────────────────────
#El corazón de la autenticación del backend.
# Acá sí empieza la lógica real de:
# Contraseñas
# hashing
# JWT
# validación de tokens
# ──────────────────────────────────────────────────────────────────────────────

# Se usan para manejar expiración del token.
from datetime import datetime, timedelta, timezone

# Crear, verificar y decodificar JWT
from jose import JWTError, jwt

# Libreria de hashing de contraseñas
from passlib.context import CryptContext

from app.Core.config import settings

# ─── Hashing (bcrypt) ─────────────────────────────────────────────────────────
# bcrypt es un algoritmo diseñado específicamente para contraseñas. No se guardan passwords reales en la DB.

#Motor del hashing de contraseñas. bcrypt es el esquema de hashing que se usará, y "auto" indica que los hashes antiguos se marcarán como obsoletos si se cambia el esquema.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Genera el hash bcrypt de una contraseña en texto plano
def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

# Verifica una contraseña en texto plano contra su hash bcrypt. Nunca se desencriptan las contraseñas.
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ─── JWT ──────────────────────────────────────────────────────────────────────


# Crea un JWT con el payload dado y una expiración opcional. El token incluirá un campo "type" para identificarlo como token de acceso.

#Payload mínimo esperado:
#        { "sub": username, "role": role }

#Se agrega automáticamente:
#        "type": "access"
#        "exp":  timestamp de expiración

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    
    
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"type": "access", "exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    #El JWT no está cirfrado, sino firmado. El payload es legible, pero la firma garantiza que no ha sido modificado. Ejemplo de payload decodificado:  

    """{
        "sub": "lucas",
        "role": "admin",
        "type": "access",
        "exp": 123456789
    }"""


# Decodifica y verifica un JWT. Retorna el payload si la firma y expiración son válidas, o None si cualquier verificación falla. También verifica que el campo "type" sea "access" para asegurarse de que es un token de acceso válido.
def decode_access_token(token: str) -> dict | None:
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
    
