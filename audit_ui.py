import asyncio
from playwright.async_api import async_playwright
import os

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Logging in...")
        await page.goto("http://localhost:3000/login")
        await page.fill("input[type='email']", "test@example.com")
        await page.fill("input[type='password']", "Password123!")
        
        # Take screenshot before clicking
        await page.screenshot(path="d:/work/stock-market/screenshot_login_before.png")
        
        await page.click("button[type='submit']")
        await page.wait_for_load_state("networkidle")
        
        # Take screenshot after clicking
        await page.screenshot(path="d:/work/stock-market/screenshot_login_after.png")
        print("Logged in!")
        
        routes = [
            {"name": "terminal", "url": "http://localhost:3000/terminal"},
            {"name": "dashboard", "url": "http://localhost:3000/dashboard"}
        ]
        
        sizes = [
            {"width": 375, "height": 812, "name": "375px"},
            {"width": 768, "height": 1024, "name": "768px"},
            {"width": 1440, "height": 900, "name": "1440px"}
        ]
        
        for route in routes:
            print(f"Navigating to {route['url']}")
            await page.goto(route['url'])
            await page.wait_for_timeout(3000) # give time for websockets/charts
            
            for size in sizes:
                print(f"Taking screenshot for {route['name']} at {size['name']}")
                await page.set_viewport_size({"width": size['width'], "height": size['height']})
                await page.wait_for_timeout(1000)
                await page.screenshot(path=f"d:/work/stock-market/screenshot_{route['name']}_{size['name']}.png", full_page=True)
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
