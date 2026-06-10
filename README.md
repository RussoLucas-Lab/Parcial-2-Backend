Backend API

API REST desarrollada con FastAPI para la gestión de productos, categorías e ingredientes.

# FoodStore v7 (Entrega Final)

## Funcionalidad

* Implementación de websocket para pedidos.
* Cloudinary para carga de imagenes en Producto y Categoría.
* MercadoPago para pagos.

## Estructura

* Nueva entidad 'UnidadMedida'
* Se eliminó el estado 'LISTO' de los pedidos.
* ProductoIngrediente ahora tiene el atributo 'unidad_medida_id' referenciando a la nueva entidad.
* Ingrediente ahora tiene el atributo stock_cantidad.

## Correcciones de parcial 2

* Bcrypt ahora implementa 12 rondas
* Frontend Admin ya no permite registrar nuevos usuarios.

---

## Tecnologías

* FastAPI
* SQLModel
* PostgreSQL
* SQLAlchemy
* Uvicorn

## Configuración

### 1. Clonar repositorio

```bash
git clone <repo-url>
cd backend
```

### 2. Crear entorno virtual

```bash
python -m venv .venv
source .venv/bin/activate   # Linux / Mac
.venv\Scripts\activate      # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Variables de entorno

Crear archivo `.env` en la raíz:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/db_name
```

##Ejecución

```bash
uvicorn app.main:app --reload
```

## 📄 Documentación automática

Disponible en:

http://localhost:8000/docs

---

## 👨‍💻 Autores

Lucas Russo
Facundo Bustamante
