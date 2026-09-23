import re

with open('backend/app/api/v1/market.py', 'r') as f:
    content = f.read()

# Replace get_indices body
content = re.sub(
    r'async def get_indices\(\) -> IndicesResponse:.*?return IndicesResponse\(indices=indices\)',
    'async def get_indices() -> IndicesResponse:\n    raise HTTPException(status_code=501, detail="Migrating to Canonical Database")\n    return IndicesResponse(indices=[])',
    content,
    flags=re.DOTALL
)

# Replace get_movers body
content = re.sub(
    r'async def get_movers\([\s\S]*?\) -> MoversResponse:.*?return MoversResponse\([\s\S]*?\)',
    'async def get_movers(exchange: str = Query("NSE"), type: str = Query("gainers")) -> MoversResponse:\n    raise HTTPException(status_code=501, detail="Migrating to Canonical Database")\n    return MoversResponse(assets=[], exchange=exchange, type=type, generated_at=datetime.now(UTC))',
    content,
    flags=re.DOTALL
)

# Replace get_heatmap body
content = re.sub(
    r'async def get_heatmap\([\s\S]*?\) -> HeatmapResponse:.*?return HeatmapResponse\([\s\S]*?\)',
    'async def get_heatmap(exchange: str = Query("NSE"), metric: str = Query("return_1d")) -> HeatmapResponse:\n    raise HTTPException(status_code=501, detail="Migrating to Canonical Database")\n    return HeatmapResponse(exchange=exchange, metric=metric, sectors={}, generated_at=datetime.now(UTC))',
    content,
    flags=re.DOTALL
)

# Replace get_global_context body
content = re.sub(
    r'async def get_global_context\(\) -> dict:.*',
    'async def get_global_context() -> dict:\n    raise HTTPException(status_code=501, detail="Migrating to Canonical Database")',
    content,
    flags=re.DOTALL
)


# Remove MarketDataService imports
content = content.replace('from app.services.market_data_service import MarketDataService', '')
content = content.replace('from app.services.data_ingestion.provider_manager import provider_manager', '')


with open('backend/app/api/v1/market.py', 'w') as f:
    f.write(content)
