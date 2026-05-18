from sqlmodel import create_engine, SQLModel, Session
#importar variables desde .env
from dotenv import load_dotenv
import os #interactuar con el sistema operativo, leer variables de entorno 

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
# <- importar variables desde .env ->
engine = create_engine(
    DATABASE_URL,
    echo = True
)

def create_db_and_tables():
        SQLModel.metadata.create_all(engine)

def get_session():
        with Session(engine) as session:
                yield session