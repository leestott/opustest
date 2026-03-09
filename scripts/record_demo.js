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

    console.log('1/7  Navigating to app...');
    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    console.log('2/7  Showing Local Path mode...');
    await page.click('button:text("Local Path")');
    await page.waitForTimeout(1500);
    await page.click('button:text("Git URL")');
    await page.waitForTimeout(1000);

    console.log('3/7  Entering repository URL...');
    await page.fill('input#git-url', REPO_URL);
    await page.waitForTimeout(1500);

    console.log('4/7  Starting verification...');
    await page.click('button#verify-btn');

    // Wait for the progress section to appear then scroll it into view
    await page.waitForSelector('#progress-section:not(.hidden)', { timeout: 10000 });
    await page.evaluate(() => {
        document.getElementById('progress-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    await page.waitForTimeout(2000);

    console.log('5/7  Watching stages progress...');
    // Track which stages we've already logged to print transitions
    const seenCompleted = new Set();
    const STAGES = ['retrieval', 'import', 'verification', 'report'];

    const maxWait = 5 * 60 * 1000; // 5 min max
    const start = Date.now();
    let done = false;

    while (Date.now() - start < maxWait) {
        // Check for completion
        const successVisible = await page.$('#success-banner:not(.hidden)');
        const errorVisible = await page.$('#error-section:not(.hidden)');
        if (successVisible) {
            done = true;
            break;
        }
        if (errorVisible) {
            console.log('     ✗ App reported an error — stopping recording.');
            // Show the error for a moment then finish
            await page.evaluate(() => {
                const el = document.getElementById('error-section');
                if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            });
            await page.waitForTimeout(3000);
            done = false;
            break;
        }

        // Keep the progress section in view — scroll to whichever stage is currently active
        for (const stage of STAGES) {
            const isActive = await page.$(`#stage-${stage}.active`);
            const isCompleted = await page.$(`#stage-${stage}.completed`);

            if (isCompleted && !seenCompleted.has(stage)) {
                seenCompleted.add(stage);
                console.log(`     ✓ ${stage} completed`);
            }

            if (isActive) {
                // Scroll the active stage into center of viewport so the viewer sees it
                await page.evaluate((s) => {
                    const el = document.getElementById('stage-' + s);
                    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, stage);
                break;
            }
        }

        await page.waitForTimeout(3000);
    }

    if (done) {
        console.log('6/7  Verification finished! Showing results...');
        await page.waitForTimeout(1000);

        // Scroll to top to show the success banner
        await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'smooth' }));
        await page.waitForTimeout(3000);

        // Now slowly scroll through the entire page to show the full report
        console.log('7/7  Scrolling through report...');
        const scrollHeight = await page.evaluate(() => document.body.scrollHeight);
        const viewportHeight = 720;
        const step = Math.round(viewportHeight * 0.4); // ~40% of viewport per step
        for (let y = 0; y < scrollHeight; y += step) {
            await page.evaluate((pos) => window.scrollTo({ top: pos, behavior: 'smooth' }), y);
            await page.waitForTimeout(1200);
        }
        // Ensure we reach the very bottom
        await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));
        await page.waitForTimeout(3000);
    } else {
        console.log('6/7  Timed out waiting for completion.');
    }

    await page.waitForTimeout(1000);

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
