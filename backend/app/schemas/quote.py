from datetime import datetime

from pydantic import BaseModel, Field


class QuoteResponse(BaseModel):
    """Schema for market quote endpoint"""

    symbol: str = Field(..., description="Ticker symbol")
    price: float = Field(..., description="Current price")
    timestamp: datetime = Field(..., description="Quote timestamp (UTC)")
    source: str = Field(..., description="Provider that supplied the data")
