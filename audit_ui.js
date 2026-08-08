const puppeteer = require('puppeteer');
const fs = require('fs');

async function run() {
    const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox', '--disable-setuid-sandbox'] });
    const page = await browser.newPage();
    
    // Login
    console.log('Logging in...');
    await page.goto('http://localhost:3000/login');
    await page.waitForSelector('input[type="email"]');
    await page.type('input[type="email"]', 'test@example.com');
    await page.type('input[type="password"]', 'Password123!');
    await page.click('button[type="submit"]');
    await page.waitForNavigation({ waitUntil: 'networkidle0' });
    console.log('Logged in!');

    const routes = [
        { name: 'terminal', url: 'http://localhost:3000/terminal' },
        { name: 'dashboard', url: 'http://localhost:3000/dashboard' }
    ];
    const sizes = [
        { width: 375, height: 812, name: '375px' },
        { width: 768, height: 1024, name: '768px' },
        { width: 1440, height: 900, name: '1440px' }
    ];

    for (const route of routes) {
        console.log(`Navigating to ${route.url}`);
        await page.goto(route.url, { waitUntil: 'networkidle2' });
        // wait for some specific elements
        await page.waitForTimeout(2000); 

        for (const size of sizes) {
            console.log(`Taking screenshot for ${route.name} at ${size.name}`);
            await page.setViewport({ width: size.width, height: size.height });
            await page.screenshot({ path: `d:/work/stock-market/screenshot_${route.name}_${size.name}.png`, fullPage: false });
        }
    }

    await browser.close();
}

run().catch(console.error);
