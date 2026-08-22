window.ATM = window.ATM || {};

window.ATM.ProgressManager = (function() {
    const activePollers = new Map();
    let isAppVisible = !document.hidden;

    // Lắng nghe trạng thái ẩn/hiện của app
    document.addEventListener('visibilitychange', () => {
        isAppVisible = !document.hidden;
    });

    const stop = (jobId) => {
        if (activePollers.has(jobId)) {
            clearTimeout(activePollers.get(jobId));
            activePollers.delete(jobId);
        }
    };

    const start = (jobId, endpointUrl, onUpdate) => {
        stop(jobId); // Chống trùng lặp (Single-flight)

        const poll = async () => {
            try {
                const status = await window.ATM.api.get(endpointUrl);
                onUpdate(status);

                if (status.done || status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                    stop(jobId);
                    return; // Backend báo xong, dọn dẹp timer
                }

                // Nếu app bị ẩn, poll chậm lại (5s). Nếu đang hiện, poll nhanh (1s).
                const delay = isAppVisible ? 1000 : 5000;
                activePollers.set(jobId, setTimeout(poll, delay));

            } catch (error) {
                console.warn(`[Polling] Job ${jobId} error, retrying...`);
                // Backoff logic: Thử lại sau 3 giây nếu gặp lỗi
                activePollers.set(jobId, setTimeout(poll, 3000));
            }
        };

        poll(); // Kích hoạt poll ngay lập tức
    };

    return { start, stop };
})();
",



