from sqlalchemy import Column, Integer
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base
Base = declarative_base()
class TradeJournal(Base):
    __tablename__ = 'dummy_tradejournal'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    created_at = Column(Integer)
    updated_at = Column(Integer)
    
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
