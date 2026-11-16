from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from src.config.settings import DATABASE_URL
_args={'connect_args':{'check_same_thread':False}} if DATABASE_URL.startswith('sqlite') else {}
engine=create_engine(DATABASE_URL, pool_pre_ping=True, **_args)
Session=sessionmaker(engine, expire_on_commit=False)
class Base(DeclarativeBase): pass
def get_db():
    with Session() as s: yield s
