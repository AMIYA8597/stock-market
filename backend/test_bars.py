from app.database.connection import engine
import pandas as pd
import asyncio

async def run():
    async with engine.begin() as conn:
        df = pd.read_sql("SELECT * FROM ohlcv", conn)
        print("Rows in ohlcv:", len(df))
        print(df.head())
        
        from nqml.features.registry import build_features
        df["time"] = pd.to_datetime(df["time"], utc=True)
        df.set_index("time", inplace=True)
        print("Time range:", df.index.min(), "to", df.index.max())
        
        features = build_features(df, "fs_v1")
        print("Features shape:", features.shape)
        
        print(features.isna().sum())

asyncio.run(run())
