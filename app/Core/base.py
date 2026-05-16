from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Column, DateTime, SQLModel, Field, func

class Base (SQLModel):
   id: Optional[int] = Field(default=None, primary_key=True)
   
   activo: bool = Field(default= True)

   created_at: datetime = Field(
      default_factory=lambda: datetime.now(timezone.utc),
      nullable=False
   )

   updated_at: datetime = Field( default_factory=lambda: datetime.now(timezone.utc), nullable=False )

   deleted_at: datetime | None = Field(default=None)

