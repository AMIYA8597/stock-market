"""
Stock screener service implementation.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis_client
from app.models.screener import SavedScreen
from app.schemas.screener import (
    SavedScreenCreate,
    SavedScreenResponse,
    ScreenerRequest,
    ScreenerResponse,
    ScreenerStatsResponse,
)


class ScreenerService:
    """Service for handling stock screening operations."""

    def __init__(self):
        self.redis = get_redis_client()
        self.data_pipeline_url = "http://data-pipeline:8001"  # Internal service URL
        self.cache_ttl = 600  # 10 minutes

    async def screen_stocks(
        self,
        request: ScreenerRequest,
        user_id: str,
        db: AsyncSession
    ) -> ScreenerResponse:
        """
        Screen stocks based on filters.
        """
        # Create cache key from filters
        filter_str = json.dumps(request.filters, sort_keys=True)
        cache_key = f"screener:{hash(filter_str)}"

        cached_data = await self.redis.get(cache_key)
        if cached_data:
            return ScreenerResponse(**json.loads(cached_data))

        try:
            # Call data pipeline for screening
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.data_pipeline_url}/screen",
                    json={
                        "filters": request.filters,
                        "sort_by": request.sort_by,
                        "sort_order": request.sort_order,
                        "limit": request.limit,
                        "offset": request.offset
                    }
                )
                response.raise_for_status()
                screen_result = response.json()

            screener_response = ScreenerResponse(
                total_count=screen_result["total_count"],
                results=screen_result["results"],
                applied_filters=request.filters,
                execution_time_ms=screen_result["execution_time_ms"],
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache the result
            await self.redis.setex(cache_key, self.cache_ttl, json.dumps(screener_response.dict()))

            return screener_response

        except httpx.RequestError as e:
            raise Exception(f"Failed to connect to data pipeline: {str(e)}")
        except httpx.HTTPStatusError as e:
            raise Exception(f"Data pipeline error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise Exception(f"Failed to screen stocks: {str(e)}")

    async def get_screener_stats(self, db: AsyncSession) -> ScreenerStatsResponse:
        """
        Get screener statistics.
        """
        cache_key = "screener_stats"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return ScreenerStatsResponse(**json.loads(cached_data))

        try:
            # Call data pipeline for stats
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(f"{self.data_pipeline_url}/stats")
                response.raise_for_status()
                stats = response.json()

            stats_response = ScreenerStatsResponse(
                total_stocks=stats["total_stocks"],
                sectors=stats["sectors"],
                market_cap_distribution=stats["market_cap_distribution"],
                pe_distribution=stats["pe_distribution"],
                last_updated=stats["last_updated"],
                timestamp=datetime.utcnow().isoformat()
            )

            # Cache for 1 hour
            await self.redis.setex(cache_key, 3600, json.dumps(stats_response.dict()))

            return stats_response

        except Exception as e:
            raise Exception(f"Failed to get screener stats: {str(e)}")

    async def save_screen(
        self,
        screen_data: SavedScreenCreate,
        user_id: str,
        db: AsyncSession
    ) -> SavedScreenResponse:
        """
        Save a stock screen.
        """
        # Create saved screen in database
        saved_screen = SavedScreen(
            user_id=user_id,
            name=screen_data.name,
            description=screen_data.description,
            filters=json.dumps(screen_data.filters),
            is_public=screen_data.is_public,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(saved_screen)
        await db.commit()
        await db.refresh(saved_screen)

        return SavedScreenResponse(
            id=str(saved_screen.id),
            user_id=saved_screen.user_id,
            name=saved_screen.name,
            description=saved_screen.description,
            filters=screen_data.filters,
            is_public=saved_screen.is_public,
            created_at=saved_screen.created_at.isoformat(),
            updated_at=saved_screen.updated_at.isoformat(),
            usage_count=0  # TODO: Track usage
        )

    async def get_saved_screens(
        self,
        user_id: str,
        db: AsyncSession
    ) -> List[SavedScreenResponse]:
        """
        Get user's saved screens.
        """
        screens_result = await db.execute(
            SavedScreen.__table__.select().where(SavedScreen.user_id == user_id)
        )
        screens = screens_result.scalars().all()

        responses = []
        for screen in screens:
            responses.append(SavedScreenResponse(
                id=str(screen.id),
                user_id=screen.user_id,
                name=screen.name,
                description=screen.description,
                filters=json.loads(screen.filters),
                is_public=screen.is_public,
                created_at=screen.created_at.isoformat(),
                updated_at=screen.updated_at.isoformat(),
                usage_count=0  # TODO: Track usage
            ))

        return responses

    async def update_saved_screen(
        self,
        screen_id: str,
        screen_data: SavedScreenCreate,
        user_id: str,
        db: AsyncSession
    ) -> SavedScreenResponse:
        """
        Update a saved screen.
        """
        screen = await db.get(SavedScreen, screen_id)
        if not screen or screen.user_id != user_id:
            raise Exception("Saved screen not found")

        screen.name = screen_data.name
        screen.description = screen_data.description
        screen.filters = json.dumps(screen_data.filters)
        screen.is_public = screen_data.is_public
        screen.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(screen)

        return SavedScreenResponse(
            id=str(screen.id),
            user_id=screen.user_id,
            name=screen.name,
            description=screen.description,
            filters=json.loads(screen.filters),
            is_public=screen.is_public,
            created_at=screen.created_at.isoformat(),
            updated_at=screen.updated_at.isoformat(),
            usage_count=0
        )

    async def delete_saved_screen(
        self,
        screen_id: str,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, str]:
        """
        Delete a saved screen.
        """
        screen = await db.get(SavedScreen, screen_id)
        if not screen or screen.user_id != user_id:
            raise Exception("Saved screen not found")

        await db.delete(screen)
        await db.commit()

        return {"message": "Saved screen deleted successfully"}

    async def get_popular_filters(self, db: AsyncSession) -> List[Dict]:
        """
        Get popular screening filters.
        """
        cache_key = "popular_filters"
        cached_data = await self.redis.get(cache_key)

        if cached_data:
            return json.loads(cached_data)

        # TODO: Implement popular filters based on usage
        popular_filters = [
            {
                "filter_name": "Value Stocks",
                "description": "Undervalued stocks with strong fundamentals",
                "usage_count": 1250,
                "filters": {
                    "pe_ratio": {"min": 5, "max": 20},
                    "pb_ratio": {"max": 2.5},
                    "roe": {"min": 15}
                }
            },
            {
                "filter_name": "Growth Stocks",
                "description": "High growth potential stocks",
                "usage_count": 980,
                "filters": {
                    "revenue_growth": {"min": 20},
                    "net_profit_growth": {"min": 25},
                    "pe_ratio": {"min": 25, "max": 50}
                }
            }
        ]

        # Cache for 1 hour
        await self.redis.setex(cache_key, 3600, json.dumps(popular_filters))

        return popular_filters

    async def get_sector_screener(
        self,
        sector: str,
        filters: Optional[Dict] = None,
        db: AsyncSession = None
    ) -> ScreenerResponse:
        """
        Screen stocks within a specific sector.
        """
        # Add sector filter
        sector_filters = {"sector": sector}
        if filters:
            sector_filters.update(filters)

        request = ScreenerRequest(
            filters=sector_filters,
            sort_by="market_cap",
            sort_order="desc",
            limit=100
        )

        return await self.screen_stocks(request, "system", db)  # system user for sector screens

    async def get_market_cap_screener(
        self,
        market_cap_category: str,  # "large", "mid", "small"
        filters: Optional[Dict] = None,
        db: AsyncSession = None
    ) -> ScreenerResponse:
        """
        Screen stocks by market capitalization category.
        """
        # Define market cap ranges (in crores)
        ranges = {
            "large": {"min": 20000},
            "mid": {"min": 5000, "max": 20000},
            "small": {"max": 5000}
        }

        if market_cap_category not in ranges:
            raise Exception("Invalid market cap category")

        cap_filters = {"market_cap": ranges[market_cap_category]}
        if filters:
            cap_filters.update(filters)

        request = ScreenerRequest(
            filters=cap_filters,
            sort_by="market_cap",
            sort_order="desc",
            limit=100
        )

        return await self.screen_stocks(request, "system", db)