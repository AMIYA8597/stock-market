import asyncio
import hashlib
import json
import logging
import uuid
from datetime import datetime, date
from pathlib import Path

import typer
import pandas as pd
from sqlalchemy import text

from app.core.database import async_session_factory
from nqml.features.registry import build_features
from nqml.labels.registry import build_label

app = typer.Typer()
logger = logging.getLogger(__name__)

async def _load_bars(universe: str, start_date: str) -> pd.DataFrame:
    """Load bars from postgres for a point-in-time universe."""
    query = text("""
        SELECT o.time,
               o.symbol_id,
               s.ticker as symbol,
               o.open, o.high, o.low, o.close, o.volume
        FROM ohlcv o
        JOIN symbols s ON s.id = o.symbol_id
        JOIN universe_memberships um ON um.symbol_id = o.symbol_id
        JOIN universes u ON u.id = um.universe_id
        WHERE u.name = :universe
          AND o.time >= :start_date
          AND o.interval = '1d'
        ORDER BY o.symbol_id, o.time
    """)
    async with async_session_factory() as session:
        result = await session.execute(query, {"universe": universe, "start_date": start_date})
        rows = result.mappings().all()

    if not rows:
        return pd.DataFrame()
        
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df.set_index("time", inplace=True)
    return df


@app.command()
def build(
    universe: str = typer.Option(..., "--universe", help="Universe name"),
    start: str = typer.Option(..., "--start", help="Start date"),
    fs: str = typer.Option(..., "--fs", help="Feature set ID"),
    label: str = typer.Option(..., "--label", help="Label spec")
):
    """Build dataset and store locally + Postgres metadata."""
    asyncio.run(_build_async(universe, start, fs, label))


async def _build_async(universe: str, start: str, fs: str, label: str):
    print(f"Building dataset for {universe} from {start} with {fs} and {label}")
    
    # 1. Load Data
    bars = await _load_bars(universe, start)
    if bars.empty:
        print("No bars found.")
        return

    # 2. Build features and labels
    all_data = []
    
    # Process per symbol to avoid cross-symbol leakage
    for symbol_id, group in bars.groupby("symbol_id", sort=False):
        group = group.sort_index()
        # Add adj_close if not present (using close as proxy if needed, ideally ohlcv has adjusted_close)
        if "adjusted_close" in group.columns:
            group["adj_close"] = group["adjusted_close"]
        else:
            group["adj_close"] = group["close"]
            
        features = build_features(group, fs)
        lbl = build_label(group, label)
        
        # Combine
        combined = features.copy()
        combined["label"] = lbl
        combined["symbol_id"] = symbol_id
        combined["symbol"] = group["symbol"]
        
        all_data.append(combined)

    if not all_data:
        print("No features built.")
        return

    final_df = pd.concat(all_data)
    
    # Drop warm-up rows (NaNs)
    # Since different features have different warm-ups, drop rows with any NaNs
    final_df = final_df.dropna()
    
    # Ensure directory
    out_dir = Path("datasets")
    out_dir.mkdir(exist_ok=True)
    
    # Hash the dataframe for content_hash
    # To be deterministic, sort by symbol_id, time and save to parquet, then hash bytes
    final_df = final_df.reset_index().sort_values(["symbol_id", "time"]).set_index("time")
    
    tmp_path = out_dir / f"tmp_{uuid.uuid4().hex}.parquet"
    final_df.to_parquet(tmp_path, engine="pyarrow", compression="zstd")
    
    with open(tmp_path, "rb") as f:
        file_bytes = f.read()
    content_hash = hashlib.sha256(file_bytes).hexdigest()
    
    out_path = out_dir / f"{content_hash}.parquet"
    if out_path.exists():
        tmp_path.unlink()
        print(f"Dataset {content_hash} already exists.")
    else:
        tmp_path.rename(out_path)
    
    # Database insert
    row_count = len(final_df)
    print(f"Dataset generated with {row_count} rows. Hash: {content_hash}")
    
    insert_query = text("""
        INSERT INTO datasets (id, content_hash, row_count, feature_set_id, label_spec, created_at)
        VALUES (:id, :content_hash, :row_count, :fs, :label, :now)
        ON CONFLICT (content_hash) DO NOTHING
    """)
    async with async_session_factory() as session:
        try:
            await session.execute(insert_query, {
                "id": str(uuid.uuid4()),
                "content_hash": content_hash,
                "row_count": row_count,
                "fs": fs,
                "label": label,
                "now": datetime.utcnow()
            })
            await session.commit()
        except Exception as e:
            print(f"Failed to insert dataset record: {e}")
            await session.rollback()

    # Generate data report
    report_dir = Path("docs/experiments/datasets")
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{content_hash}.md"
    
    missing_rates = final_df.isna().mean().to_dict()
    rows_per_sym = final_df.groupby("symbol").size().to_dict()
    
    # Class balance per year
    final_df["year"] = final_df.index.year
    balance = final_df.groupby(["year", "label"]).size().unstack(fill_value=0).to_dict(orient="index")
    
    min_date = final_df.index.min()
    max_date = final_df.index.max()
    
    report = [
        f"# Dataset Report: {content_hash}",
        f"- **Feature Set**: {fs}",
        f"- **Label Spec**: {label}",
        f"- **Universe**: {universe}",
        f"- **Total Rows**: {row_count}",
        f"- **Date Range**: {min_date.date() if pd.notnull(min_date) else 'N/A'} to {max_date.date() if pd.notnull(max_date) else 'N/A'}",
        "",
        "## Class Balance per Year",
    ]
    for yr, counts in balance.items():
        report.append(f"- **{yr}**: {counts}")
    
    report.extend(["", "## Rows per Symbol"])
    for sym, count in list(rows_per_sym.items())[:10]: # show top 10
        report.append(f"- {sym}: {count}")
    if len(rows_per_sym) > 10:
        report.append(f"- ... and {len(rows_per_sym)-10} more")
        
    report.extend(["", "## Missing Rates per Feature (should be 0)"])
    for f_name, rate in missing_rates.items():
        if rate > 0:
            report.append(f"- {f_name}: {rate:.2%}")
            
    with open(report_path, "w") as f:
        f.write("\n".join(report))
        
    print(f"Report written to {report_path}")
    print("\nSUMMARY:\n" + "\n".join(report[:15]))
