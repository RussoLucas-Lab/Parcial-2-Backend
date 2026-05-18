from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Relationship, SQLModel, Field

from app.modules.Usuario.model import Usuario


class RefreshToken(SQLModel, table=True):
   __tablename__ = "refresh_token"

   id: Optional[int] = Field(default=None, primary_key=True)
   usuario_id: int = Field(foreign_key="usuario.id", nullable=False)

   token_hash: str = Field(max_length=64, unique=True, nullable=False)

   expires_at: datetime = Field(nullable=False)

   revoked_at: Optional[datetime] = Field(default=None)
   created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      nullable=False,
   )

   usuario: "Usuario" = Relationship(
   back_populates="refresh_tokens"
)