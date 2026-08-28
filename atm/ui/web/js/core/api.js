window.ATM = window.ATM || {};
window.ATM.store = {
    get: (key, defVal) => {
        try { 
            const val = localStorage.getItem(key);
            if (val === null || val === undefined) return defVal;
            return JSON.parse(val) ?? defVal; 
        }
        catch(e) { return defVal; }
    },
    set: (key, val) => {
        try { localStorage.setItem(key, JSON.stringify(val)); }
        catch(e) { console.error('Storage error', e); }
    }
};

/**
 * ATM.api - Core Fetch Wrapper
 * Đảm bảo Timeout, Parse JSON tự động, và cung cấp AbortController.
 */
(function() {
    const DEFAULT_TIMEOUT = 60000; // 60 seconds (Add game/extract can take a while)

    class NetworkError extends Error {
        constructor(message) {
            super(message);
            this.name = "NetworkError";
        }
    }

    class BackendError extends Error {
        constructor(message, status) {
            super(message);
            this.name = "BackendError";
            this.status = status;
        }
    }

    async function fetchWithTimeout(resource, options = {}) {
        const timeout = options.timeout || DEFAULT_TIMEOUT;
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(new Error("Timeout")), timeout);

        let finalSignal = controller.signal;
        if (options.signal) {
            if (AbortSignal.any) {
                finalSignal = AbortSignal.any([controller.signal, options.signal]);
            } else {
                const composite = new AbortController();
                const abort = () => composite.abort();
                controller.signal.addEventListener('abort', abort);
                options.signal.addEventListener('abort', abort);
                if (controller.signal.aborted || options.signal.aborted) abort();
                finalSignal = composite.signal;
            }
        }

        const response = await fetch(resource, {
            ...options,
            signal: finalSignal
        });
        
        clearTimeout(id);
        return response;
    }

    window.ATM.api = {
        NetworkError,
        BackendError,
        
        async get(endpoint, options = {}) {
            try {
                const sep = endpoint.includes('?') ? '&' : '?';
                const url = `/api/${endpoint}${sep}t=${Date.now()}`;
                const response = await fetchWithTimeout(url, options);
                if (!response.ok) {
                    throw new BackendError(`HTTP Error: ${response.status}`, response.status);
                }
                const data = await response.json();
                if (data.status === 'error') {
                    const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.server_error') : "Lỗi xử lý từ máy chủ";
                    throw new BackendError(data.error || fallback, response.status);
                }
                return data;
            } catch (error) {
                if (error.name === 'AbortError') {
                    if (options.signal && options.signal.aborted) {
                        throw error;
                    }
                    throw new NetworkError("Request timed out.");
                }
                throw error;
            }
        },

        async post(endpoint, data = {}, options = {}) {
            try {
                const response = await fetchWithTimeout(`/api/${endpoint}`, {
                    ...options,
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new BackendError(errorData.error || `HTTP Error: ${response.status}`, response.status);
                }
                const resData = await response.json();
                if (resData.status === 'error') {
                    const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.server_error') : "Lỗi xử lý từ máy chủ";
                    throw new BackendError(resData.error || fallback, response.status);
                }
                return resData;
            } catch (error) {
                if (error.name === 'AbortError') {
                    if (options.signal && options.signal.aborted) {
                        throw error;
                    }
                    throw new NetworkError("Request timed out.");
                }
                throw error;
            }
        }
    };
})();

