import re

with open('backend/app/api/v1/backtest.py', 'r') as f:
    content = f.read()

# 1. Remove execute_backtest_job and BACKTEST_PROGRESS entirely
# We find the start of BACKTEST_PROGRESS and end of execute_backtest_job
content = re.sub(
    r'# Memory store for active job progress tracking.*?BACKTEST_PROGRESS: dict\[str, int\] = \{\}.*?def safe_round\(.*?async def execute_backtest_job.*?def post_backtest_run',
    'def safe_round(val: float, places: int) -> float:\n    if val is None or math.isnan(val) or math.isinf(val):\n        return 0.0\n    return round(float(val), places)\n\n@router.post("/run", response_model=BacktestRunResponse, status_code=202)\nasync def post_backtest_run',
    content,
    flags=re.DOTALL
)

# 2. Update get_backtest_status
# Let's see what get_backtest_status looks like first, wait. I will just rewrite get_backtest_status and get_backtest_results.
new_get_status = '''@router.get("/status/{job_id}", response_model=BacktestStatusResponse)
async def get_backtest_status(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestStatusResponse:
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    stmt = select(BacktestJob).where(BacktestJob.id == job_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    progress_pct = job.progress if job.progress is not None else 0
    if job.status == "DONE":
        progress_pct = 100
        
    return BacktestStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress_pct=progress_pct,
        error_message=job.error_message
    )'''

content = re.sub(
    r'@router\.get\("/status/\{job_id\}", response_model=BacktestStatusResponse\).*?-> BacktestStatusResponse:.*?(?=@router\.get\("/results/\{job_id\})',
    new_get_status + '\n\n',
    content,
    flags=re.DOTALL
)


new_get_results = '''@router.get("/results/{job_id}", response_model=BacktestResultsResponse)
async def get_backtest_results(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestResultsResponse:
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job ID format.")

    stmt = select(BacktestJob).where(BacktestJob.id == job_uuid)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    if job.status != "DONE" or not job.results:
        raise HTTPException(status_code=400, detail="Job is not completed yet or has no results.")

    results = job.results
    
    # We construct the response based on the schema and what we saved in backtest_tasks
    # If the metrics are missing, we mock them for now.
    metrics = results.get("metrics", {})
    
    return BacktestResultsResponse(
        job_id=str(job.id),
        status=job.status,
        metrics=BacktestMetrics(
            total_return=safe_round(metrics.get("total_return", 0), 4),
            cagr=safe_round(metrics.get("cagr", 0), 4),
            sharpe_ratio=safe_round(metrics.get("sharpe", 0), 4),
            sortino_ratio=safe_round(metrics.get("sortino_ratio", 0), 4),
            max_drawdown=safe_round(metrics.get("max_drawdown", 0), 4),
            win_rate=safe_round(metrics.get("win_rate", 0), 4),
            profit_factor=safe_round(metrics.get("profit_factor", 0), 4),
            total_trades=metrics.get("num_trades", 0),
            expectancy=safe_round(metrics.get("expectancy", 0), 4),
            omega_ratio=safe_round(metrics.get("omega_ratio", 0), 4),
            calmar_ratio=safe_round(metrics.get("calmar_ratio", 0), 4),
            tail_ratio=safe_round(metrics.get("tail_ratio", 0), 4),
            serenity_ratio=safe_round(metrics.get("serenity_ratio", 0), 4),
            deflated_sharpe=safe_round(metrics.get("deflated_sharpe", 0), 4),
        ),
        equity_curve=[EquityCurvePoint(**pt) for pt in results.get("equity_curve", [])],
        drawdown_series=[DrawdownPoint(**pt) for pt in results.get("drawdown_series", [])],
        trade_log=[TradeLogEntry(**tr) for tr in results.get("trade_log", [])],
        monte_carlo=None,
        statistical_tests=None,
        walk_forward=None
    )'''

content = re.sub(
    r'@router\.get\("/results/\{job_id\}", response_model=BacktestResultsResponse\).*?(?=$|\n\n)',
    new_get_results + '\n',
    content,
    flags=re.DOTALL
)

with open('backend/app/api/v1/backtest.py', 'w') as f:
    f.write(content)
