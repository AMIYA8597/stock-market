import asyncio

from app.services.data_ingestion.nse_source import NSESource


async def test():
    n = NSESource()
    res = await n.get_quote('RELIANCE.NS')
    print(res.price)

if __name__ == "__main__":
    asyncio.run(test())
