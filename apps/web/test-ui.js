const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  
  // Capture console messages from the page
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.error('PAGE ERROR:', err.message));
  page.on('requestfailed', request => {
    console.error(`REQUEST FAILED: ${request.url()} - ${request.failure()?.errorText}`);
  });
  page.on('response', response => {
    console.log(`RESPONSE: ${response.url()} - ${response.status()}`);
  });

  console.log('Navigating to login page...');
  await page.goto('http://localhost:3000/login', { waitUntil: 'networkidle2', timeout: 120000 });
  
  console.log('Filling out login form...');
  await page.type('input[type="email"]', 'test@example.com');
  await page.type('input[type="password"]', 'Password123!');
  
  console.log('Submitting login form...');
  await page.click('button[type="submit"]');

  // Wait for 5 seconds to see what happens after click
  await new Promise(resolve => setTimeout(resolve, 5000));
  
  const currentUrl = page.url();
  console.log('Current URL after login attempt:', currentUrl);
  
  await browser.close();
})();
