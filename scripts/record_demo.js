/**
 * Records a ~1 minute demo video of the Code Verification System.
 * Uses Playwright's built-in video recording.
 *
 * Usage: npx playwright test scripts/record_demo.js
 * Or:    node scripts/record_demo.js
 */
const { chromium } = require('playwright');
const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const APP_URL = process.env.APP_URL || 'https://ca-eopp3marjvhai.graycoast-a1fffbe4.eastus2.azurecontainerapps.io';
const REPO_URL = 'https://github.com/leestott/copperhead-bot';
const VIDEO_DIR = path.join(__dirname, '..', 'screenshots');
const OUTPUT_MP4 = path.join(VIDEO_DIR, 'demo.mp4');

(async () => {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        recordVideo: {
            dir: VIDEO_DIR,
            size: { width: 1280, height: 720 }
        },
        viewport: { width: 1280, height: 720 }
    });

    const page = await context.newPage();

    console.log('1/6  Navigating to app...');
    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('2/6  Showing Local Path mode...');
    await page.click('button:text("Local Path")');
    await page.waitForTimeout(1500);
    await page.click('button:text("Git URL")');
    await page.waitForTimeout(1000);

    console.log('3/6  Entering repository URL...');
    await page.fill('input#git-url', REPO_URL);
    await page.waitForTimeout(1500);

    console.log('4/6  Starting verification...');
    await page.click('button#verify-btn');

    // Wait for the progress section to appear
    await page.waitForSelector('#progress-section:not(.hidden)', { timeout: 10000 });
    await page.waitForTimeout(2000);

    console.log('5/6  Waiting for verification to complete (this takes a few minutes)...');
    // Poll for completion — check for success banner or error
    const maxWait = 5 * 60 * 1000; // 5 min max
    const start = Date.now();
    let done = false;
    while (Date.now() - start < maxWait) {
        const successVisible = await page.$('#success-banner:not(.hidden)');
        const errorVisible = await page.$('#error-section:not(.hidden)');
        if (successVisible || errorVisible) {
            done = true;
            break;
        }
        await page.waitForTimeout(5000);
    }

    if (done) {
        console.log('6/6  Verification finished! Scrolling through report...');
        await page.waitForTimeout(2000);

        // Slowly scroll down to show the report
        for (let i = 0; i < 5; i++) {
            await page.mouse.wheel(0, 300);
            await page.waitForTimeout(1500);
        }
    } else {
        console.log('6/6  Timed out waiting for completion.');
    }

    await page.waitForTimeout(2000);

    // Get the .webm path before closing (path is known, but file is finalized on close)
    const webmPath = await page.video().path();

    // Close context to finalize video
    await context.close();
    await browser.close();

    // Convert .webm to .mp4 using ffmpeg
    console.log(`\nConverting to MP4...`);
    try {
        execSync(
            `ffmpeg -y -i "${webmPath}" -c:v libx264 -preset fast -crf 23 -pix_fmt yuv420p "${OUTPUT_MP4}"`,
            { stdio: 'pipe' }
        );
        // Remove the intermediate .webm file
        fs.unlinkSync(webmPath);
        console.log(`Video saved to: ${OUTPUT_MP4}`);
    } catch (err) {
        console.error('ffmpeg conversion failed. Is ffmpeg installed?');
        console.error(err.message);
        console.log(`Raw .webm saved to: ${webmPath}`);
    }

    console.log('Done!');
})();
