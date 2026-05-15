# ── Config ────────────────────────────────────────────────────────────────────
# centro de configuración del backend. Su objetivo es:
    # leer variables desde .env
    # evitar hardcodear secretos
    # centralizar configuración de JWT y base de datos
    # permitir cambiar entornos fácilmente (dev, test, producción)
# ──────────────────────────────────────────────────────────────────────────────

from pydantic import computed_field

# BaseSettings es una clase de Pydantic que permite definir configuraciones que se pueden cargar desde variables de entorno o archivos .env
from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    # ─── Base de datos ────────────────────────────────────────────────────────
    postgres_user:     str = "postgres"
    postgres_password: str = "postgres"
    postgres_db:       str = "seguridad_jwt_db"
    postgres_host:     str = "localhost"
    postgres_port:     int = 5433

# @property permite que el método DATABASE_URL() se use como si fuera un atributo normal (settings.DATABASE_URL) sin necesidad de llamarlo con paréntesis. @computed_field le indica a Pydantic que ese atributo forma parte del modelo y debe tratarse como un campo calculado oficialmente. En este caso, ambos se usan para construir automáticamente la URL de conexión a la base de datos a partir de las variables individuales (postgres_user, postgres_password, etc.), evitando tener que escribir la URL manualmente.

    @computed_field
    @property   
    def DATABASE_URL(self) -> str:
        
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    # ─── JWT ─────────────────────────────────────────────────────────────────

    # La llave no tiene valor default, lo que obliga a definirla en el .env para evitar hardcodear secretos en el código. 
    SECRET_KEY: str   

    # El algoritmo de hashing para JWT se establece en HS256, que es un algoritmo simétrico comúnmente utilizado.                 
    ALGORITHM:  str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Configuración de Pydantic para cargar variables de entorno desde un archivo .env y manejar casos donde falten variables sin lanzar errores, lo que es útil para entornos de desarrollo o pruebas donde no todas las variables pueden estar definidas.
    model_config = {
        "env_file":          ".env",
        "env_file_encoding": "utf-8",
        "extra":             "ignore",   
    }

    # ─── Instancia Global ───────────────────────────────────────────────────
    # instancia global de configuración queasegura que toda la aplicación use la misma configuración centralizada.


settings = Settings()