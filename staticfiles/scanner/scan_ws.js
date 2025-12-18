(() => {
    const container = document.getElementById("scan-container");
    if (!container) return;

    const scanId = container.dataset.scanId;
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const socketUrl = `${scheme}://${location.host}/ws/scan/${scanId}/`;

    const socket = new WebSocket(socketUrl);

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        // Progress
        if (data.progress !== undefined) {
            document.getElementById("progress-bar").style.width = `${data.progress}%`;
            document.getElementById("progress-text").innerText = `${data.progress}% completed`;
        }

        // Status
        if (data.status) {
            document.getElementById("scan-status").innerText = data.status;
        }

        // Steps
        if (data.steps) {
            for (const [step, value] of Object.entries(data.steps)) {
                const el = document.getElementById(`step-${step}`);
                if (el) el.innerText = value;
            }
        }

        // Live log
        if (data.log) {
            const logBox = document.getElementById("live-log");
            const line = document.createElement("div");
            line.innerText = data.log;
            logBox.appendChild(line);
            logBox.scrollTop = logBox.scrollHeight;
        }
    };

    socket.onclose = () => {
        console.warn("Scan WebSocket closed");
    };
})();
