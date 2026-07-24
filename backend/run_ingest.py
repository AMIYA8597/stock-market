import asyncio

from app.services.data_ingestion.orchestrator import DataOrchestrator


async def main():
    print("Ingesting RELIANCE.NS data via Orchestrator...")
    orc = DataOrchestrator()
    res = await orc.ingest_historical('RELIANCE.NS', '1d', 730)
    print("Ingestion complete. Result:", res)

if __name__ == "__main__":
    asyncio.run(main())
