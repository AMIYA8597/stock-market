import re

with open('backend/app/api/v1/predictions.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace generate_forecast to return 503
new_func = '''@router.post("/forecast")
async def generate_forecast(
    payload: ForecastRequest, _rate_limit: None = Depends(get_rate_limiter(requests=10, window=60))
):
    raise HTTPException(
        status_code=503,
        detail={"code": "FORECAST_NOT_AVAILABLE"}
    )'''
    
content = re.sub(
    r'@router\.post\("/forecast"\).*?return result',
    new_func,
    content,
    flags=re.DOTALL
)

with open('backend/app/api/v1/predictions.py', 'w', encoding='utf-8') as f:
    f.write(content)
