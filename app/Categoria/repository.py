from sqlmodel import Session, select, text

from app.Categoria.model import Categoria
from app.Core.repository import BaseRepository


class CategoriaRepository(BaseRepository[Categoria]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Categoria)
    
    def get_by_id(self, record_id: int) -> Categoria | None:
        return self.session.exec(
            select(Categoria)
            .where(Categoria.id == record_id)
            .where(Categoria.activo == True)
        ).first()

    def get_by_ids(self, ids: list[int]):
        if not ids:
            return []

        statement = select(self.model).where(self.model.id.in_(ids))
        return self.session.exec(statement).all()

    def get_by_nombre(self, nombre: str) -> Categoria | None:    
        return self.session.exec(
            select(Categoria).where(Categoria.nombre == nombre)
        ).first()

    def get_all(self, offset = 0, limit = 20):
        return super().get_all(offset, limit)

    def get_active(self, offset: int = 0, limit: int = 20) -> list[Categoria]:
        return list(
            self.session.exec(
                select(Categoria)
                .where(Categoria.activo == True)
            )
        )
    
    def count(self) -> int:
        return len(self.session.exec(select(Categoria)).all())
    
    # ── Categoria Tree ────────────────────────────────────────────────────────────────────
    # El método get_tree en el repository se encarga de ir a la base de datos y traer todas las categorías relacionadas usando una query SQL recursiva (WITH RECURSIVE). Empieza por las categorías raíz (las que no tienen parent_id) y va recorriendo sus hijos, nietos, etc., devolviendo el resultado como una lista plana de filas donde cada registro incluye su id y su parent_id. Es importante entender que acá todavía no hay un árbol como tal, sino solo datos “desordenados” pero con la información necesaria para reconstruir la jerarquía.
    # ──────────────────────────────────────────────────────────────────────────────────────

    def get_tree(self) ->list [dict]:
        result = self.session.exec(
            text(
                """
                WITH RECURSIVE tree AS (
                    SELECT id, parent_id, nombre, descripcion, imagen_url, 0 AS depth
                    FROM categoria
                    WHERE parent_id IS NULL AND activo = true

                    UNION ALL

                    SELECT c.id, c.parent_id, c.nombre, c.descripcion, c.imagen_url, t.depth + 1
                    FROM categoria c
                    JOIN tree t ON c.parent_id = t.id
                    WHERE c.activo = true
                )
                SELECT * FROM tree ORDER BY depth, nombre;
                """
            )
        ).all()
        return [dict(row._mapping) for row in result]