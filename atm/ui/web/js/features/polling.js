window.ATM = window.ATM || {};

window.ATM.ProgressManager = (function() {
    const activePollers = new Map();
    let isAppVisible = !document.hidden;

    // Lắng nghe trạng thái ẩn/hiện của app
    document.addEventListener('visibilitychange', () => {
        isAppVisible = !document.hidden;
    });

    const stop = (gameId) => {
        if (activePollers.has(gameId)) {
            clearTimeout(activePollers.get(gameId));
            activePollers.delete(gameId);
        }
    };

    const start = (gameId, onUpdate) => {
        stop(gameId); // Chống trùng lặp (Single-flight)

        const poll = async () => {
            try {
                const status = await window.ATM.api.get(`games/translation-status?game_id=${gameId}`);
                onUpdate(status);

                if (status.done) {
                    stop(gameId);
                    return; // Backend báo xong, dọn dẹp timer
                }

                // Nếu app bị ẩn, poll chậm lại (5s). Nếu đang hiện, poll nhanh (1s).
                const delay = isAppVisible ? 1000 : 5000;
                activePollers.set(gameId, setTimeout(poll, delay));

            } catch (error) {
                console.warn(`[Polling] Game ${gameId} gặp lỗi mạng, đang thử lại...`);
                // Backoff logic: Thử lại sau 3 giây nếu gặp lỗi
                activePollers.set(gameId, setTimeout(poll, 3000));
            }
        };

        poll(); // Kích hoạt poll ngay lập tức
    };

    return { start, stop };
})();
