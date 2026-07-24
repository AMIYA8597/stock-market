const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage();
  
  // Set viewport to 1440px
  await page.setViewport({ width: 1440, height: 900 });
  
  // Navigate to terminal for RELIANCE
  await page.goto('http://localhost:3000/terminal?symbol=RELIANCE.NS', { waitUntil: 'networkidle2' });
  
  // Wait for the chart or signal panel to render
  await page.waitForTimeout(5000); // Give it some time to fetch data
  
  // Take screenshot
  await page.screenshot({ path: 'screenshot_1440px.png' });
  
  // Mobile screenshot 360px
  await page.setViewport({ width: 360, height: 800 });
  await page.screenshot({ path: 'screenshot_360px.png' });
  
  await browser.close();
})();
