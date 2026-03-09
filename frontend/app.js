/* global document, fetch, EventSource */

const STAGE_ORDER = ["retrieval", "import", "verification", "report"];
const STAGE_ICONS = { pending: "\u25CB", active: "\u25D4", completed: "\u2714", error: "\u2716" };

function startVerification() {
    const dirInput = document.getElementById("directory-path");
    const directoryPath = dirInput.value.trim();
    if (!directoryPath) {
        alert("Please enter a directory path.");
        return;
    }

    // Reset UI
    resetProgressUI();
    document.getElementById("progress-section").classList.remove("hidden");
    document.getElementById("error-section").classList.add("hidden");
    document.getElementById("report-section").classList.add("hidden");
    document.getElementById("verify-btn").disabled = true;

    // Start SSE via fetch (POST with body — EventSource only supports GET)
    fetchSSE(directoryPath);
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

async function fetchSSE(directoryPath) {
    try {
        var response = await fetch("/api/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ directory_path: directoryPath }),
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
