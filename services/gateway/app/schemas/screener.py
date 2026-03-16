"""
Pydantic schemas for screener endpoints.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ScreenerFilter(BaseModel):
    """Individual screener filter."""
    field: str = Field(..., description="Field to filter on")
    operator: str = Field(..., description="Filter operator")
    value: float = Field(..., description="Filter value")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v):
        """Validate filter operator."""
        valid_operators = [
            "eq", "ne", "gt", "gte", "lt", "lte",
            "between", "in", "not_in", "contains"
        ]
        if v not in valid_operators:
            raise ValueError(f"Invalid operator. Must be one of: {', '.join(valid_operators)}")
        return v


class ScreenerRequest(BaseModel):
    """Stock screener request."""
    filters: List[ScreenerFilter] = Field(default_factory=list, max_items=20)
    sort_by: str = Field(default="market_cap", description="Sort field")
    sort_order: str = Field(default="desc", description="Sort order")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Results offset")

    @field_validator("sort_order")
    @classmethod
    def validate_sort_order(cls, v):
        """Validate sort order."""
        if v not in ["asc", "desc"]:
            raise ValueError("sort_order must be 'asc' or 'desc'")
        return v


class ScreenerResult(BaseModel):
    """Individual screener result."""
    symbol: str
    name: str
    sector: str
    market_cap: Optional[float]
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    dividend_yield: Optional[float]
    roe: Optional[float]
    debt_to_equity: Optional[float]
    revenue_growth: Optional[float]
    net_profit_growth: Optional[float]
    current_price: float
    change_percent: float
    volume: int


class ScreenerResponse(BaseModel):
    """Screener response."""
    total_count: int
    results: List[ScreenerResult]
    applied_filters: List[ScreenerFilter]
    execution_time_ms: int


class SavedScreenCreate(BaseModel):
    """Create saved screen request."""
    name: str = Field(..., min_length=1, max_length=100, description="Screen name")
    description: Optional[str] = Field(None, max_length=500, description="Screen description")
    filters: List[ScreenerFilter] = Field(..., max_items=20, description="Screen filters")
    is_public: bool = Field(default=False, description="Make screen public")


class SavedScreenUpdate(BaseModel):
    """Update saved screen request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    filters: Optional[List[ScreenerFilter]] = Field(None, max_items=20)
    is_public: Optional[bool] = None


class SavedScreenResponse(BaseModel):
    """Saved screen response."""
    id: str
    user_id: str
    name: str
    description: Optional[str]
    filters: List[ScreenerFilter]
    is_public: bool
    created_at: str
    updated_at: str
    usage_count: int


class ScreenerStatsResponse(BaseModel):
    """Screener statistics response."""
    total_stocks: int
    sectors: Dict[str, int]
    market_cap_distribution: Dict[str, int]
    pe_distribution: Dict[str, int]
    last_updated: str


class ScreenerResponse(BaseModel):
    """Generic screener response."""
    success: bool
    message: str
    data: Optional[dict] = None