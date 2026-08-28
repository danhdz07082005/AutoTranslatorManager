window.ATM = window.ATM || {};

window.ATM.ProgressManager = (function() {
    const activePollers = new Map();
    let isAppVisible = true;

    document.addEventListener('visibilitychange', () => {
        isAppVisible = !document.hidden;
    });

    const stop = (jobId) => {
        if (activePollers.has(jobId)) {
            const poller = activePollers.get(jobId);
            if (poller.timer) clearTimeout(poller.timer);
            if (poller.controller) poller.controller.abort();
            activePollers.delete(jobId);
        }
    };

    const start = (jobId, endpointUrl, onUpdate) => {
        stop(jobId); 
        let retries = 0;
        const maxRetries = 10;

        const poll = async () => {
            const controller = new AbortController();
            activePollers.set(jobId, { timer: null, controller });
            
            try {
                const status = await window.ATM.api.get(endpointUrl, { signal: controller.signal });
                retries = 0; // reset retries on success
                
                if (onUpdate) onUpdate(status);

                if (status.done || status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
                    stop(jobId);
                    return; 
                }

                const delay = isAppVisible ? 1000 : 5000;
                const timer = setTimeout(poll, delay);
                activePollers.set(jobId, { timer, controller: null });

            } catch (error) {
                if (error.name === 'AbortError') return; // User stopped it
                
                retries++;
                console.warn(`[Polling] Job ${jobId} error (${retries}/${maxRetries}), retrying...`);
                if (retries > maxRetries) {
                    console.error(`[Polling] Job ${jobId} failed after max retries.`);
                    stop(jobId);
                    if (onUpdate) onUpdate({ status: 'failed', error: 'Max retries reached' });
                    return;
                }
                const backoff = Math.min(3000 * Math.pow(1.5, retries), 15000); // Max 15s
                const timer = setTimeout(poll, backoff);
                activePollers.set(jobId, { timer, controller: null });
            }
        };

        poll();
    };

    return { start, stop };
})();
