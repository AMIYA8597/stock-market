from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class PasswordResetToken(Base):
    __tablename__ = 'dummy_passwordresettoken'
    id = Column(Integer, primary_key=True)
class RefreshSession(Base):
    __tablename__ = 'dummy_refreshsession'
    id = Column(Integer, primary_key=True)
