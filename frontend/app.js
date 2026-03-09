/* global document, fetch, EventSource */

const STAGE_ORDER = ["retrieval", "import", "verification", "report"];
const STAGE_ICONS = { pending: "\u25CB", active: "\u25CF", completed: "\u2714", error: "\u2716" };
const STAGE_PROGRESS = { retrieval: 25, import: 50, verification: 75, report: 100 };

var currentInputMode = "git";
var timerInterval = null;
var startTime = null;
var abortController = null;

function setInputMode(mode) {
    currentInputMode = mode;
    document.getElementById("git-input-group").classList.toggle("hidden", mode !== "git");
    document.getElementById("local-input-group").classList.toggle("hidden", mode !== "local");
    document.getElementById("mode-git").classList.toggle("active", mode === "git");
    document.getElementById("mode-local").classList.toggle("active", mode === "local");
}

function startVerification() {
    var payload;
    if (currentInputMode === "git") {
        var gitUrl = document.getElementById("git-url").value.trim();
        if (!gitUrl) {
            showInlineError("git-url", "Please enter a Git repository URL.");
            return;
        }
        payload = { git_url: gitUrl };
    } else {
        var directoryPath = document.getElementById("directory-path").value.trim();
        if (!directoryPath) {
            showInlineError("directory-path", "Please enter a directory path.");
            return;
        }
        payload = { directory_path: directoryPath };
    }

    // Reset UI
    resetProgressUI();
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("error-section").classList.add("hidden");
    document.getElementById("report-section").classList.add("hidden");
    document.getElementById("success-banner").classList.add("hidden");
    setVerifyBtnLoading(true);

    // Start elapsed timer
    startElapsedTimer();

    // Start SSE via fetch (POST with body — EventSource only supports GET)
    fetchSSE(payload);
}

function cancelVerification() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    stopElapsedTimer();
    setVerifyBtnLoading(false);
    showError("Verification cancelled by user.");
}

function retryVerification() {
    document.getElementById("error-section").classList.add("hidden");
    startVerification();
}

function setVerifyBtnLoading(loading) {
    var btn = document.getElementById("verify-btn");
    var btnText = document.getElementById("verify-btn-text");
    var btnSpinner = document.getElementById("verify-btn-spinner");
    var cancelBtn = document.getElementById("cancel-btn");
    btn.disabled = loading;
    btnText.textContent = loading ? "Verifying\u2026" : "Verify Codebase";
    btnSpinner.classList.toggle("hidden", !loading);
    cancelBtn.classList.toggle("hidden", !loading);
}

function showInlineError(inputId, message) {
    var input = document.getElementById(inputId);
    input.classList.add("input-error");
    input.setAttribute("title", message);
    input.focus();
    setTimeout(function () {
        input.classList.remove("input-error");
        input.removeAttribute("title");
    }, 3000);
}

function startElapsedTimer() {
    startTime = Date.now();
    var timerEl = document.getElementById("elapsed-timer");
    timerEl.textContent = "0:00";
    timerInterval = setInterval(function () {
        var elapsed = Math.floor((Date.now() - startTime) / 1000);
        var mins = Math.floor(elapsed / 60);
        var secs = elapsed % 60;
        timerEl.textContent = mins + ":" + (secs < 10 ? "0" : "") + secs;
    }, 1000);
}

function stopElapsedTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function resetProgressUI() {
    STAGE_ORDER.forEach(function (stage) {
        var el = document.getElementById("stage-" + stage);
        el.className = "progress-stage";
        el.querySelector(".stage-icon").textContent = STAGE_ICONS.pending;
        document.getElementById("msg-" + stage).textContent = "";
    });
    document.getElementById("progress-bar-fill").style.width = "0%";
}

function updateStage(stage, message, status) {
    var stageEl = document.getElementById("stage-" + stage);
    if (!stageEl) return;
    stageEl.className = "progress-stage " + status;
    stageEl.querySelector(".stage-icon").textContent = STAGE_ICONS[status] || STAGE_ICONS.pending;
    document.getElementById("msg-" + stage).textContent = message;

    // Update progress bar
    if (status === "active" || status === "completed") {
        var pct = STAGE_PROGRESS[stage] || 0;
        if (status === "active") pct = Math.max(pct - 20, 5);
        var bar = document.getElementById("progress-bar-fill");
        var current = parseInt(bar.style.width) || 0;
        if (pct > current) bar.style.width = pct + "%";
    }
}

async function fetchSSE(payload) {
    abortController = new AbortController();
    try {
        var response = await fetch("/api/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
            signal: abortController.signal,
        });

        if (!response.ok) {
            showError("Server returned status " + response.status + ". Please try again.");
            return;
        }

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = "";

        while (true) {
            var result = await reader.read();
            if (result.done) break;

            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (var i = 0; i < lines.length; i++) {
                var line = lines[i].trim();
                if (line.startsWith("data: ")) {
                    var jsonStr = line.substring(6);
                    try {
                        var event = JSON.parse(jsonStr);
                        handleEvent(event);
                    } catch (_e) {
                        // Ignore malformed JSON
                    }
                }
            }
        }

        // If stream ends without a complete/error event, treat as error
        if (!document.getElementById("report-section").classList.contains("hidden") === false &&
            document.getElementById("error-section").classList.contains("hidden")) {
            showError("The verification stream ended unexpectedly. The server may have timed out.");
        }
    } catch (err) {
        if (err.name === "AbortError") return; // cancelled by user
        showError("Connection error: " + err.message);
    } finally {
        abortController = null;
        stopElapsedTimer();
        setVerifyBtnLoading(false);
    }
}

function handleEvent(event) {
    if (event.type === "progress") {
        updateStage(event.stage, event.message, "active");
        // Mark prior stages as completed
        var idx = STAGE_ORDER.indexOf(event.stage);
        for (var i = 0; i < idx; i++) {
            var prev = STAGE_ORDER[i];
            var el = document.getElementById("stage-" + prev);
            if (!el.classList.contains("completed")) {
                updateStage(prev, "Done", "completed");
            }
        }
    } else if (event.type === "complete") {
        // Mark all stages completed
        STAGE_ORDER.forEach(function (s) {
            updateStage(s, "Done", "completed");
        });
        document.getElementById("progress-bar-fill").style.width = "100%";
        stopElapsedTimer();
        showSuccessBanner();
        showReport(event.report);
    } else if (event.type === "error") {
        // Mark the current active stage as error
        STAGE_ORDER.forEach(function (s) {
            var el = document.getElementById("stage-" + s);
            if (el.classList.contains("active")) {
                updateStage(s, "Failed", "error");
            }
        });
        stopElapsedTimer();
        showError(event.message);
    }
}

function showSuccessBanner() {
    var banner = document.getElementById("success-banner");
    banner.classList.remove("hidden");
    var elapsed = startTime ? Math.floor((Date.now() - startTime) / 1000) : 0;
    var mins = Math.floor(elapsed / 60);
    var secs = elapsed % 60;
    var timeStr = mins > 0 ? mins + "m " + secs + "s" : secs + "s";
    document.getElementById("success-summary").textContent =
        "All 4 verification areas analyzed in " + timeStr;
}

function showReport(htmlContent) {
    var section = document.getElementById("report-section");
    section.classList.remove("hidden");
    var container = document.getElementById("report-container");

    // Use a sandboxed iframe to render the HTML report safely
    var iframe = document.createElement("iframe");
    iframe.sandbox = "allow-same-origin";
    container.innerHTML = "";
    container.appendChild(iframe);

    var iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
    iframeDoc.open();
    iframeDoc.write(htmlContent);
    iframeDoc.close();

    // Auto-resize iframe to content height
    iframe.onload = function () {
        iframe.style.height = iframeDoc.documentElement.scrollHeight + "px";
    };
    // Fallback resize
    setTimeout(function () {
        iframe.style.height = iframeDoc.documentElement.scrollHeight + "px";
    }, 500);

    // Smooth scroll to report
    section.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showError(message) {
    var section = document.getElementById("error-section");
    section.classList.remove("hidden");
    document.getElementById("error-message").textContent = message;
    section.scrollIntoView({ behavior: "smooth", block: "start" });
}
