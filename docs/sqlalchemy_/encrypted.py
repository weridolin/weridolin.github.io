import sqlalchemy as sa
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os

SQLALCHEMY_URL = "sqlite:///" + \
    os.path.join(os.path.dirname(__file__), 'scheduler.db')

engine = sa.create_engine(
    SQLALCHEMY_URL,
    echo=True)
SessionFactory = sessionmaker(bind=engine, autoflush=True)