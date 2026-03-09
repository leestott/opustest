/* global document, fetch, EventSource */

const STAGE_ORDER = ["retrieval", "import", "verification", "report"];
const STAGE_ICONS = { pending: "\u25CB", active: "\u25D4", completed: "\u2714", error: "\u2716" };

var currentInputMode = "git";

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
            alert("Please enter a Git repository URL.");
            return;
        }
        payload = { git_url: gitUrl };
    } else {
        var directoryPath = document.getElementById("directory-path").value.trim();
        if (!directoryPath) {
            alert("Please enter a directory path.");
            return;
        }
        payload = { directory_path: directoryPath };
    }

    // Reset UI
    resetProgressUI();
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("error-section").classList.add("hidden");
    document.getElementById("report-section").classList.add("hidden");
    document.getElementById("verify-btn").disabled = true;

    // Start SSE via fetch (POST with body — EventSource only supports GET)
    fetchSSE(payload);
}

function resetProgressUI() {
    STAGE_ORDER.forEach(function (stage) {
        var el = document.getElementById("stage-" + stage);
        el.className = "progress-stage";
        el.querySelector(".stage-icon").textContent = STAGE_ICONS.pending;
        document.getElementById("msg-" + stage).textContent = "";
    });
}

function updateStage(stage, message, status) {
    var stageEl = document.getElementById("stage-" + stage);
    if (!stageEl) return;
    stageEl.className = "progress-stage " + status;
    stageEl.querySelector(".stage-icon").textContent = STAGE_ICONS[status] || STAGE_ICONS.pending;
    document.getElementById("msg-" + stage).textContent = message;
}

async function fetchSSE(payload) {
    try {
        var response = await fetch("/api/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

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
    } catch (err) {
        showError("Connection error: " + err.message);
    } finally {
        document.getElementById("verify-btn").disabled = false;
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
        showReport(event.report);
    } else if (event.type === "error") {
        showError(event.message);
    }
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
}

function showError(message) {
    var section = document.getElementById("error-section");
    section.classList.remove("hidden");
    document.getElementById("error-message").textContent = message;
}
