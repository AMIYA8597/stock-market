from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class ModelArtifact(Base):
    __tablename__ = 'dummy_modelartifact'
    id = Column(Integer, primary_key=True)
