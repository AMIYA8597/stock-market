from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.user import Base


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    total_value = Column(Numeric(20, 2), default=0)
    cash_balance = Column(Numeric(20, 2), default=0)
    is_active = Column(Boolean, default=True)
    strategy = Column(String(100), nullable=True)  # Investment strategy
    risk_profile = Column(String(50), nullable=True)  # Conservative, Moderate, Aggressive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="portfolios")
    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    quantity = Column(Numeric(20, 4), nullable=False)
    average_price = Column(Numeric(20, 2), nullable=False)
    current_price = Column(Numeric(20, 2), nullable=True)
    market_value = Column(Numeric(20, 2), nullable=True)
    unrealized_pnl = Column(Numeric(20, 2), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    portfolio = relationship("Portfolio", back_populates="holdings")