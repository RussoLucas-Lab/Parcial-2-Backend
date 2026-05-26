from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.DireccionEntrega.unit_of_work import DireccionEntregaUnitOfWork
from app.modules.DireccionEntrega.model import DireccionEntrega
from app.modules.DireccionEntrega.schemas import (
    DireccionEntregaCreate,
    DireccionEntregaList,
    DireccionEntregaPublic,
    DireccionEntregaUpdate,
)


class DireccionEntregaService:
    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ───────────────────────────────────────────────────────

    def _get_or_404(self, uow: DireccionEntregaUnitOfWork, direccion_id: int) -> DireccionEntrega:
        direccion = uow.direcciones.get_by_id(direccion_id)
        if not direccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DireccionEntrega con id {direccion_id} no encontrada",
            )
        return direccion

    def _assert_usuario_exists(self, uow: DireccionEntregaUnitOfWork, usuario_id: int) -> None:
        if not uow.usuarios.get_by_id(usuario_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Usuario con id {usuario_id} no encontrado",
            )

    def _assert_pertenece_al_usuario(
        self, direccion: DireccionEntrega, usuario_id: int
    ) -> None:
        if direccion.usuario_id != usuario_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"DireccionEntrega con id {direccion.id} no encontrada para el usuario {usuario_id}",
            )

    # ── Casos de uso ──────────────────────────────────────────────────────────

    def create(self, usuario_id: int, data: DireccionEntregaCreate) -> DireccionEntregaPublic:
        with DireccionEntregaUnitOfWork(self._session) as uow:
            self._assert_usuario_exists(uow, usuario_id)

            direccion = DireccionEntrega(usuario_id=usuario_id, **data.model_dump())
            uow.direcciones.add(direccion)

            result = DireccionEntregaPublic.model_validate(direccion)

        return result

    def list_by_usuario(
        self, usuario_id: int, offset: int = 0, limit: int = 20
    ) -> DireccionEntregaList:
        with DireccionEntregaUnitOfWork(self._session) as uow:
            self._assert_usuario_exists(uow, usuario_id)

            direcciones = uow.direcciones.get_by_usuario_id(usuario_id, offset, limit)
            total = uow.direcciones.count_by_usuario(usuario_id)

            result = DireccionEntregaList(
                data=[DireccionEntregaPublic.model_validate(d) for d in direcciones],
                total=total,
            )

        return result

    def get_by_id(self, usuario_id: int, direccion_id: int) -> DireccionEntregaPublic:
        with DireccionEntregaUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id)
            self._assert_pertenece_al_usuario(direccion, usuario_id)

            result = DireccionEntregaPublic.model_validate(direccion)

        return result

    def update(
        self, usuario_id: int, direccion_id: int, data: DireccionEntregaUpdate ) -> DireccionEntregaPublic:

        with DireccionEntregaUnitOfWork(self._session) as uow:

            direccion = self._get_or_404(uow, direccion_id)
            self._assert_pertenece_al_usuario(direccion, usuario_id)

            patch = data.model_dump(exclude_unset=True)
      
            if patch.get("es_principal") is True:

                direccion_principal = (
                    uow.direcciones.get_principal_by_usuario(usuario_id)
                )

                if (
                    direccion_principal
                    and direccion_principal.id != direccion.id
                ):
                    direccion_principal.es_principal = False
                    uow.direcciones.add(direccion_principal)

            for field, value in patch.items():
                setattr(direccion, field, value)

            direccion.updated_at = datetime.now(timezone.utc)

            uow.direcciones.add(direccion)

            result = DireccionEntregaPublic.model_validate(direccion)

            return result


    def soft_delete(self, usuario_id: int, direccion_id: int) -> None:
        with DireccionEntregaUnitOfWork(self._session) as uow:
            direccion = self._get_or_404(uow, direccion_id)
            self._assert_pertenece_al_usuario(direccion, usuario_id)

            direccion.activo = False
            direccion.deleted_at = datetime.now(timezone.utc)
            uow.direcciones.add(direccion)
