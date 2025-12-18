(function () {
    const root = document.getElementById("scan-root");
    if (!root) return;

    const scanId = root.dataset.scanId;
    const scheme = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${scheme}://${location.host}/ws/scan/${scanId}/`);

    socket.onmessage = function (e) {
        const data = JSON.parse(e.data);

        if (data.progress !== undefined) {
            document.getElementById("progress-bar").style.width = `${data.progress}%`;
        }

        if (data.status) {
            document.getElementById("scan-status").innerText = data.status;
        }

        if (data.type === "complete") {
            socket.close();
        }
    };
})();
