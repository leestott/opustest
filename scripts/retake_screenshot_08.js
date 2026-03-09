/**
 * Retakes ALL 8 screenshots at a zoomed-out level so the full screen is shown.
 * Mocks UI states for progress screenshots (04-07) to avoid needing a live verification.
 *
 * Usage: node scripts/retake_screenshot_08.js
 */
const { chromium } = require('playwright');
const path = require('path');

const APP_URL = process.env.APP_URL || 'https://ca-eopp3marjvhai.graycoast-a1fffbe4.eastus2.azurecontainerapps.io';
const REPO_URL = 'https://github.com/leestott/copperhead-bot';
const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

const SAMPLE_REPORT_HTML = `<!DOCTYPE html>
<html>
<head><style>
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;padding:20px;background:#f8f9fa;color:#1a1a2e}
.header{text-align:center;padding:20px;background:linear-gradient(135deg,#0078d4,#00a4ef);color:#fff;border-radius:8px;margin-bottom:24px}
.header h1{margin:0 0 8px;font-size:1.8rem}
.total-score{font-size:3rem;font-weight:700;margin:8px 0}
.score-cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.score-card{background:#fff;border-radius:8px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.08);border-top:4px solid #0078d4}
.score-card h3{margin:0 0 8px;font-size:.85rem;color:#555}
.score-card .score{font-size:2rem;font-weight:700;color:#0078d4}
h2{color:#16213e;border-bottom:2px solid #e8e8e8;padding-bottom:6px}
table{width:100%;border-collapse:collapse;table-layout:fixed;margin-top:16px}
th{background:#0078d4;color:#fff;padding:12px;text-align:left;font-size:.85rem}
td{padding:12px;border:1px solid #ddd;vertical-align:top;word-wrap:break-word;overflow-wrap:break-word;white-space:normal;font-size:.85rem}
tr:nth-child(even){background:#f8f9fa}
th:nth-child(1),td:nth-child(1){width:25%}
th:nth-child(2),td:nth-child(2){width:10%}
th:nth-child(3),td:nth-child(3){width:10%}
th:nth-child(4),td:nth-child(4){width:30%}
th:nth-child(5),td:nth-child(5){width:25%}
</style></head>
<body>
<div class="header">
<h1>Code Verification Report</h1>
<p>Repository: copperhead-bot</p>
<div class="total-score">16 / 20</div>
<p>Overall Score</p>
</div>
<div class="score-cards">
<div class="score-card"><h3>Static Code Quality</h3><div class="score">4 / 5</div></div>
<div class="score-card"><h3>Functional Correctness</h3><div class="score">5 / 5</div></div>
<div class="score-card"><h3>Known Error Handling</h3><div class="score">3 / 5</div></div>
<div class="score-card"><h3>Unknown Error Handling</h3><div class="score">4 / 5</div></div>
</div>
<h2>Errors Found</h2>
<table>
<thead><tr><th>Error Found</th><th>File</th><th>Type</th><th>Explanation</th><th>Fix Prompt</th></tr></thead>
<tbody>
<tr><td>Missing type hints on function parameters</td><td>bot.py</td><td>Code Quality</td><td>Functions lack type annotations, reducing readability and IDE support. PEP 484 recommends type hints for all public APIs.</td><td>Add type hints to all function parameters and return types in bot.py following PEP 484 conventions.</td></tr>
<tr><td>Bare except clause catches all exceptions</td><td>handlers.py</td><td>Known Errors</td><td>Using bare 'except:' catches SystemExit and KeyboardInterrupt. Should catch specific exception types.</td><td>Replace bare except clauses in handlers.py with specific exception types (e.g., except ValueError, except ConnectionError).</td></tr>
<tr><td>No logging for API call failures</td><td>api_client.py</td><td>Unknown Errors</td><td>API calls lack logging when exceptions occur, making production debugging difficult. The standard library logging module should be used.</td><td>Add logging.error() calls in except blocks within api_client.py to capture API failure details including status codes and response bodies.</td></tr>
<tr><td>Missing input validation on user commands</td><td>commands.py</td><td>Known Errors</td><td>User-supplied command arguments are not validated before processing, which could lead to unexpected behaviour with malformed input.</td><td>Add input validation for all user command arguments in commands.py, checking for expected types, lengths, and allowed values before processing.</td></tr>
</tbody>
</table>
</body>
</html>`;

// Helper: set stage states by applying CSS classes and updating icons
function setStageStates(stageMap) {
    // stageMap: { retrieval: 'completed'|'active'|'pending', ... }
    const ICONS = { pending: '\u25CB', active: '\u25CF', completed: '\u2714' };
    for (const [stage, state] of Object.entries(stageMap)) {
        const el = document.getElementById('stage-' + stage);
        if (!el) continue;
        el.classList.remove('active', 'completed');
        if (state !== 'pending') el.classList.add(state);
        el.querySelector('.stage-icon').textContent = ICONS[state] || ICONS.pending;
    }
}

(async () => {
    const browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({
        viewport: { width: 1280, height: 900 },
        deviceScaleFactor: 2
    });
    const page = await context.newPage();

    async function shot(name) {
        const file = path.join(SCREENSHOT_DIR, name);
        await page.screenshot({ path: file });
        console.log('  -> ' + name);
    }

    // ── Load the app ──
    console.log('Loading app...');
    await page.goto(APP_URL, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);

    // ── 01 Landing page ──
    console.log('01  Landing page (Git URL mode)');
    await shot('01-landing-page.png');

    // ── 02 Local Path mode ──
    console.log('02  Local Path mode');
    await page.click('button#mode-local');
    await page.waitForTimeout(800);
    await shot('02-local-path-mode.png');

    // ── 03 Repository URL entered ──
    console.log('03  Repository URL entered');
    await page.click('button#mode-git');
    await page.waitForTimeout(400);
    await page.fill('input#git-url', REPO_URL);
    await page.waitForTimeout(800);
    await shot('03-url-entered.png');

    // ── 04 Stage 1: Retrieval in progress ──
    console.log('04  Stage 1 — retrieval active');
    await page.evaluate((setStageStatesCode) => {
        // Show progress section
        document.getElementById('progress-section').classList.remove('hidden');
        // Set progress bar to 25%
        document.getElementById('progress-bar-fill').style.width = '25%';
        // Set elapsed timer
        document.getElementById('elapsed-timer').textContent = '0:12';
        // Disable verify button
        const btn = document.getElementById('verify-btn');
        btn.disabled = true;
        document.getElementById('verify-btn-text').textContent = 'Verifying\u2026';
        document.getElementById('verify-btn-spinner').classList.remove('hidden');
        document.getElementById('cancel-btn').classList.remove('hidden');
        // Set stage states
        const ICONS = { pending: '\u25CB', active: '\u25CF', completed: '\u2714' };
        const stageMap = { retrieval: 'active', import: 'pending', verification: 'pending', report: 'pending' };
        for (const [stage, state] of Object.entries(stageMap)) {
            const el = document.getElementById('stage-' + stage);
            if (!el) continue;
            el.classList.remove('active', 'completed');
            if (state !== 'pending') el.classList.add(state);
            el.querySelector('.stage-icon').textContent = ICONS[state];
        }
        document.getElementById('msg-retrieval').textContent = 'Retrieving Python coding examples from database\u2026';
        // Scroll progress into view
        document.getElementById('progress-section').scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(600);
    await shot('04-stage1-retrieval.png');

    // ── 05 Stage 3: Verification agents running ──
    console.log('05  Stage 3 — verification active');
    await page.evaluate(() => {
        document.getElementById('progress-bar-fill').style.width = '75%';
        document.getElementById('elapsed-timer').textContent = '1:34';
        const ICONS = { pending: '\u25CB', active: '\u25CF', completed: '\u2714' };
        const stageMap = { retrieval: 'completed', import: 'completed', verification: 'active', report: 'pending' };
        for (const [stage, state] of Object.entries(stageMap)) {
            const el = document.getElementById('stage-' + stage);
            if (!el) continue;
            el.classList.remove('active', 'completed');
            if (state !== 'pending') el.classList.add(state);
            el.querySelector('.stage-icon').textContent = ICONS[state];
        }
        document.getElementById('msg-retrieval').textContent = 'Retrieved 24 examples';
        document.getElementById('msg-import').textContent = 'Imported 8 Python files';
        document.getElementById('msg-verification').textContent = 'Running 4 verification agents\u2026';
        document.getElementById('progress-section').scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(600);
    await shot('05-stage3-verification.png');

    // ── 06 Stage 4: Report generation ──
    console.log('06  Stage 4 — report generation active');
    await page.evaluate(() => {
        document.getElementById('progress-bar-fill').style.width = '90%';
        document.getElementById('elapsed-timer').textContent = '2:48';
        const ICONS = { pending: '\u25CB', active: '\u25CF', completed: '\u2714' };
        const stageMap = { retrieval: 'completed', import: 'completed', verification: 'completed', report: 'active' };
        for (const [stage, state] of Object.entries(stageMap)) {
            const el = document.getElementById('stage-' + stage);
            if (!el) continue;
            el.classList.remove('active', 'completed');
            if (state !== 'pending') el.classList.add(state);
            el.querySelector('.stage-icon').textContent = ICONS[state];
        }
        document.getElementById('msg-retrieval').textContent = 'Retrieved 24 examples';
        document.getElementById('msg-import').textContent = 'Imported 8 Python files';
        document.getElementById('msg-verification').textContent = 'All 4 areas scored';
        document.getElementById('msg-report').textContent = 'Generating HTML report\u2026';
        document.getElementById('progress-section').scrollIntoView({ behavior: 'instant', block: 'start' });
    });
    await page.waitForTimeout(600);
    await shot('06-stage4-report-generation.png');

    // ── 07 Verification complete (success banner) ──
    console.log('07  Verification complete — success banner');
    await page.evaluate(() => {
        document.getElementById('progress-bar-fill').style.width = '100%';
        document.getElementById('elapsed-timer').textContent = '3:05';
        const ICONS = { completed: '\u2714' };
        ['retrieval', 'import', 'verification', 'report'].forEach(stage => {
            const el = document.getElementById('stage-' + stage);
            if (!el) return;
            el.classList.remove('active');
            el.classList.add('completed');
            el.querySelector('.stage-icon').textContent = ICONS.completed;
        });
        document.getElementById('msg-report').textContent = 'Report ready';
        // Re-enable verify button
        const btn = document.getElementById('verify-btn');
        btn.disabled = false;
        document.getElementById('verify-btn-text').textContent = 'Verify Codebase';
        document.getElementById('verify-btn-spinner').classList.add('hidden');
        document.getElementById('cancel-btn').classList.add('hidden');
        // Show success banner
        const banner = document.getElementById('success-banner');
        banner.classList.remove('hidden');
        document.getElementById('success-summary').textContent = 'All 4 verification areas analyzed in 3m 5s';
        // Scroll to top to show the full page with the success banner
        window.scrollTo({ top: 0, behavior: 'instant' });
    });
    await page.waitForTimeout(600);
    await shot('07-verification-complete.png');

    // ── 08 Report detail with Copilot button ──
    console.log('08  Report detail + Copilot button');
    await page.evaluate((html) => {
        // Hide input section and progress to focus on report
        document.getElementById('input-section').style.display = 'none';
        document.getElementById('progress-section').classList.add('hidden');
        document.getElementById('success-banner').classList.add('hidden');

        // Show report section
        const section = document.getElementById('report-section');
        section.classList.remove('hidden');

        // Create iframe
        const container = document.getElementById('report-container');
        const iframe = document.createElement('iframe');
        iframe.sandbox = 'allow-same-origin';
        iframe.style.width = '100%';
        iframe.style.border = 'none';
        container.innerHTML = '';
        container.appendChild(iframe);

        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(html);
        iframeDoc.close();

        setTimeout(() => {
            iframe.style.height = iframeDoc.documentElement.scrollHeight + 'px';
        }, 300);

        // Show export button
        document.getElementById('export-btn-row').style.display = 'flex';

        // Scroll to report
        section.scrollIntoView({ behavior: 'instant', block: 'start' });
    }, SAMPLE_REPORT_HTML);

    await page.waitForTimeout(1500);

    // Resize iframe properly
    await page.evaluate(() => {
        const iframe = document.querySelector('#report-container iframe');
        if (iframe) {
            const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
            iframe.style.height = iframeDoc.documentElement.scrollHeight + 'px';
        }
    });
    await page.waitForTimeout(500);

    // Take 08 as full-page to show scores + table + Copilot button
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08-report-detail.png'), fullPage: true });
    console.log('  -> 08-report-detail.png (full page)');

    await context.close();
    await browser.close();
    console.log('\nAll 8 screenshots captured!');
})();
