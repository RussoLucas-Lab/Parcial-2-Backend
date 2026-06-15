# Tests de Integración — Food Store Backend

Suite de tests de integración para el proyecto Food Store, construida con **pytest** y **FastAPI TestClient** sobre una base de datos **SQLite in-memory**.

---

## Requisitos previos

Tener el entorno virtual activado con las dependencias instaladas:

```bash
# Desde la raíz del proyecto
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

> No se necesita PostgreSQL corriendo. Los tests usan SQLite in-memory de forma automática.

---

## Ejecutar los tests

### Todos los tests

```bash
pytest tests/ -v
```

### Un archivo específico

```bash
pytest tests/test_auth.py -v
pytest tests/test_pedidos.py -v
pytest tests/test_estadisticas.py -v
```

### Un test específico por nombre

```bash
pytest tests/test_auth.py::TestLogin::test_login_ok -v
pytest tests/test_pedidos.py::TestAvanzarEstado::test_avanzar_estado_valido_pendiente_a_confirmado -v
```

### Solo tests que fallan

```bash
pytest tests/ -v --lf
```

### Incluyendo tests marcados como xfail

```bash
pytest tests/ -v --runxfail
```

### Mostrando print/logs durante los tests

```bash
pytest tests/ -v -s
```

---

## Estructura de archivos

```
tests/
├── conftest.py           # Fixtures compartidas (engine, client, factories, auth)
├── test_auth.py          # Tests de autenticación (register, login, logout)
├── test_pedidos.py       # Tests de pedidos (crear, FSM de estados, RBAC)
├── test_estadisticas.py  # Tests de estadísticas (solo rol ADMIN)
└── README.md             # Este archivo
```

---

## Qué cubre cada archivo

### `test_auth.py`
| Test | Descripción |
|------|-------------|
| `test_register_ok` | Registro de usuario nuevo → 201 con rol CLIENT |
| `test_register_duplicado_retorna_409` | Email ya registrado → 409 |
| `test_login_ok` | Login correcto → 200, cookies seteadas |
| `test_login_credenciales_invalidas_retorna_401` | Password incorrecta → 401 |
| `test_logout_revoca_token` | Logout revoca sesión, acceso posterior → 401 |
| `test_rate_limit` | ⏭️ SKIP — rate limiting no implementado |

### `test_pedidos.py`
| Test | Descripción |
|------|-------------|
| `test_crear_pedido_ok` | Pedido válido → 201 con totales calculados |
| `test_crear_pedido_producto_inexistente_retorna_404` | Producto inexistente → 404 |
| `test_crear_pedido_stock_insuficiente` | ⚠️ XFAIL — stock no validado aún |
| `test_avanzar_estado_valido_pendiente_a_confirmado` | PENDIENTE → CONFIRMADO (rol PEDIDOS) |
| `test_avanzar_estado_invalido_terminal_retorna_403` | ENTREGADO → EN_PREP → 403 (RN-01) |
| `test_cancelar_pedido_con_rol_pedidos` | PEDIDOS cancela pedido → CANCELADO |
| `test_rol_client_no_puede_cambiar_estado` | CLIENT intenta cambiar estado → 403 |
| `test_historial_append_only` | ⚠️ XFAIL — historial no guardado aún |
| `test_transiciones_actualizan_estado_del_pedido` | Secuencia PENDIENTE→CONFIRMADO→EN_PREP→ENTREGADO |

### `test_estadisticas.py`
| Test | Descripción |
|------|-------------|
| `test_estadisticas_requieren_admin` | Sin auth → 401 |
| `test_estadisticas_rol_client_retorna_403` | CLIENT → 403 |
| `test_facturacion_total_con_pedidos` | Suma correcta de pedidos |
| `test_cantidad_pedidos_con_pedidos` | Conteo correcto |
| `test_facturacion_por_periodo` | Responde lista `{fecha, total}` |
| `test_pedidos_por_periodo` | Responde lista `{fecha, cantidad}` |
| `test_top_productos_retorna_lista` | Ranking de productos más vendidos |
| `test_ingresos_solo_approved` | ⚠️ XFAIL — no filtrado por estado de pago |
| `test_cancelado_no_suma_en_facturacion` | ⚠️ XFAIL — CANCELADO sí suma actualmente |

---

## Leyenda de marcadores

| Símbolo | Significado |
|---------|-------------|
| ✅ | Test activo, debe pasar |
| ⏭️ SKIP | Funcionalidad no implementada, se omite |
| ⚠️ XFAIL | Se espera que falle (feature pendiente de implementar) |

---

## Decisiones técnicas

### SQLite in-memory
Cada test genera su propia base de datos SQLite in-memory desde cero. Garantiza aislamiento total sin necesidad de rollbacks manuales.

### Auth por cookies
El login no devuelve tokens en el body (solo `expires_in`). Los tokens viajan en cookies `HTTPOnly`. El `TestClient` maneja el jar de cookies automáticamente igual que un browser.

### Variables de entorno
Los tests **no necesitan** un archivo `.env` configurado. Se sobreescriben las dependencias de base de datos directamente en los fixtures.

---

## Features pendientes de implementar

Estos tests están marcados como `xfail` y pasarán automáticamente una vez implementadas las features:

1. **Validación de stock** en `PedidoService.create()`:
   ```python
   if producto.stock_cantidad < item.cantidad:
       raise HTTPException(400, "Stock insuficiente")
   ```

2. **Historial de estados** en `PedidoService.avanzar_estado()`:
   ```python
   uow.session.add(HistorialEstadoPedido(
       pedido_id=pedido_id,
       estado_desde=origen,
       estado_hacia=destino,
       usuario_id=current_user.id,
   ))
   ```

3. **Rate limiting** en login (ej: `slowapi`).

4. **Filtro por estado de pago** en estadísticas de facturación.
