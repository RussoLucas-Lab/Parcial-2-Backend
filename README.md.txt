Backend API

API REST desarrollada con FastAPI para la gestión de productos, categorías e ingredientes.

## Tecnologías

* FastAPI
* SQLModel
* PostgreSQL
* SQLAlchemy
* Uvicorn

## Estructura del Proyecto

```
app/
├── Core/              
├── Producto/
├── Categoria/
├── Ingrediente/
└── main.py
```

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

## 👨‍💻 Autor

Lucas Russo
