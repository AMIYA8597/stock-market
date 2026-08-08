const puppeteer = require('puppeteer');
const fs = require('fs');

(async () => {
  console.log('Launching browser...');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER:', msg.text()));

  // Set viewport to a typical desktop size
  await page.setViewport({ width: 1280, height: 800 });

  console.log('Navigating to http://localhost:3000/test-chart...');
  try {
    await page.goto('http://localhost:3000/test-chart', { waitUntil: 'networkidle2', timeout: 15000 });
  } catch (e) {
    console.log('Navigation error (might just be timeout):', e.message);
  }

  // Wait a bit for websocket data and chart rendering
  console.log('Waiting for chart to render...');
  await new Promise(r => setTimeout(r, 5000));
  
  console.log('Reloading to fix Fast Refresh issues...');
  await page.reload({ waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 5000));

  // Take screenshot
  const screenshotPath = 'C:\\Users\\USER\\.gemini\\antigravity\\brain\\755e8706-7fdd-45f4-a4b9-2abab251020b\\chart_render.png';
  await page.screenshot({ path: screenshotPath });
  console.log(`Screenshot saved to ${screenshotPath}`);

  await browser.close();
})();
