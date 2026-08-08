import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("http://localhost:3000/login")
        await page.fill("input[type='email']", "test@example.com")
        await page.fill("input[type='password']", "Password123!")
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        
        await page.goto("http://localhost:3000/terminal")
        await page.set_viewport_size({"width": 375, "height": 812})
        await page.wait_for_timeout(3000)
        
        # Click "AI Trade" tab on mobile
        await page.click("text=AI Trade")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="d:/work/stock-market/screenshot_terminal_375px_aitrade.png", full_page=True)
        
        # Click "Orders" tab
        await page.click("text=Orders")
        await page.wait_for_timeout(1000)
        await page.screenshot(path="d:/work/stock-market/screenshot_terminal_375px_orders.png", full_page=True)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
