from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlmodel import Session

from app.modules.Categoria.schemas import CategoriaCreate, CategoriaList, CategoriaPublic, CategoriaTree, CategoriaUpdate

from app.modules.Categoria.unit_of_work import CategoriaUnitOfWork
from app.modules.Categoria.model import Categoria


class CategoriaService:

    def __init__(self, session: Session) -> None:
        self._session = session

    # ── Helpers privados ───────────────────────────────────────────────────────────

    def _get_or_404(self, uow: CategoriaUnitOfWork, categoria_id: int) -> Categoria:
        categoria = uow.categorias.get_by_id(categoria_id)
        if not categoria:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoria con id {categoria_id} no encontrada",
            )
        return categoria

    def _assert_nombre_unique(self, uow: CategoriaUnitOfWork, nombre: str) -> None:
        if uow.categorias.get_by_nombre(nombre):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"El nombre '{nombre}' ya está en uso",
            )

    def _assert_parent_exists(
        self, uow: CategoriaUnitOfWork, parent_id: int | None
    ) -> None:
        if parent_id is None:
            return

        parent = uow.categorias.get_by_id(parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Categoria padre con id {parent_id} no encontrada",
            )
    

    # ── Build Tree ────────────────────────────────────────────────────────────────────
    # El método _build_tree del service toma la lista plana que devuelve el repository y la transforma en una estructura jerárquica real.
    
    # Primero crea objetos CategoriaTree para cada fila y los guarda en un diccionario por id; luego recorre nuevamente los datos para vincular cada categoría con su padre usando parent_id, agregándola dentro de subcategorias. Finalmente, devuelve solo las categorías raíz, que ya contienen recursivamente todos sus hijos, formando así el árbol completo listo para ser retornado por la API.
    # ──────────────────────────────────────────────────────────────────────────────────────


    def _build_tree(self, rows: list[dict]) -> list[CategoriaTree]:
        nodes: dict[int, CategoriaTree] = {}
        roots: list[CategoriaTree] = []

        for row in rows:
            node = CategoriaTree(
                id = row["id"],
                nombre = row["nombre"],
                descripcion = row.get("descripcion"),
                imagen_url = row.get("imagen_url"),
                parent_id = row.get("parent_id")
            )
            nodes[row["id"]] = node

        for row in rows:
            node = nodes[row["id"]]
            pid = row.get("parent_id")
            if pid and pid in nodes:
                nodes[pid].subcategorias.append(node)
            else:
                roots.append(node)
        
        return roots


    # ── Casos de uso ──────────────────────────────────────────────────────────────

    def create(self, data: CategoriaCreate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            self._assert_nombre_unique(uow, data.nombre)
            self._assert_parent_exists(uow, data.parent_id)

            categoria = Categoria.model_validate(data)
            uow.categorias.add(categoria)

            result = CategoriaPublic.model_validate(categoria)

        return result

    def get_all(self, offset: int = 0, limit: int = 20) -> CategoriaList:
        with CategoriaUnitOfWork(self._session) as uow:
            categorias = uow.categorias.get_active(offset=offset, limit=limit)
            total = uow.categorias.count()

            result = CategoriaList(
                data=[CategoriaPublic.model_validate(c) for c in categorias],
                total=total,
            )

            return result

    def get_by_id(self, categoria_id: int) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)
            result = CategoriaPublic.model_validate(categoria)

        return result

    def update(self, categoria_id: int, data: CategoriaUpdate) -> CategoriaPublic:
        with CategoriaUnitOfWork(self._session) as uow:
            categoria = self._get_or_404(uow, categoria_id)

        
            if data.nombre and data.nombre != categoria.nombre:
                self._assert_nombre_unique(uow, data.nombre)

            # Validacion del Parent y verificar que no sea su propio Parent
            if data.parent_id is not None:
                self._assert_parent_exists(uow, data.parent_id)
                
                if data.parent_id == categoria.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Una categoria no puede ser su propio padre",
                    )

            patch = data.model_dump(exclude_unset=True)
            for field, value in patch.items():
                setattr(categoria, field, value)

            categoria.updated_at = datetime.now(timezone.utc)
            uow.categorias.add(categoria)

            result = CategoriaPublic.model_validate(categoria)

        return result

    def soft_delete(self, categoria_id: int) -> None:
        with CategoriaUnitOfWork(self._session) as uow:

            categoria = self._get_or_404(uow, categoria_id)

            productos_activos = [
            producto
            for producto in categoria.productos
            if producto.activo
        ]

            if productos_activos:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No se puede eliminar la categoría porque tiene productos activos asociados."
                )

            categoria.activo = False
            categoria.deleted_at = datetime.now(timezone.utc)
            
            uow.categorias.add(categoria)

    # ── TREEs ──────────────────────────────────────────────────────────────

    def get_all_tree(self) -> list[CategoriaTree]:
        with CategoriaUnitOfWork(self._session) as uow:
            
            rows = uow.categorias.get_tree()
       
        return self._build_tree(rows)