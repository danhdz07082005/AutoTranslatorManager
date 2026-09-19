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
        constructor(message, status, code = null) {
            super(message);
            this.name = "BackendError";
            this.status = status;
            this.code = code;
        }
    }

    async function fetchWithTimeout(resource, options = {}) {
        const timeout = options.timeout || DEFAULT_TIMEOUT;
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(new Error("Timeout")), timeout);

        let finalSignal = controller.signal;
        let composite = null;
        let abort = null;
        if (options.signal) {
            if (options.signal.aborted) {
                controller.abort();
            } else {
                composite = new AbortController();
                abort = () => composite.abort();
                controller.signal.addEventListener('abort', abort);
                options.signal.addEventListener('abort', abort);
                if (controller.signal.aborted || options.signal.aborted) abort();
                finalSignal = composite.signal;
            }
        }

        try {
            const response = await fetch(resource, {
                ...options,
                signal: finalSignal
            });
            clearTimeout(id);
            return response;
        } finally {
            if (abort && options.signal) {
                options.signal.removeEventListener('abort', abort);
                controller.signal.removeEventListener('abort', abort);
            }
        }
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
                    const errorData = await response.json().catch(() => ({}));
                    const i18n = window.ATM.i18n;
                    const params = errorData.params || { error: errorData.error || '' };
                    const localizedMsg = (errorData.code && i18n ? i18n.t(errorData.code, params) : null)
                        || (errorData.error && i18n ? i18n.t(errorData.error, params) : null)
                        || errorData.error
                        || `HTTP Error: ${response.status}`;
                    const err = new BackendError(localizedMsg, response.status, errorData.code);
                    err.data = errorData;
                    throw err;
                }
                const data = await response.json();
                if (data.status === 'error') {
                    const i18n = window.ATM.i18n;
                    const params = data.params || { error: data.error || '' };
                    const localizedMsg = (data.code && i18n ? i18n.t(data.code, params) : null)
                        || (data.error && i18n ? i18n.t(data.error, params) : null)
                        || data.error
                        || (i18n ? i18n.t('toast.server_error') : 'Server error');
                    const err = new BackendError(localizedMsg, response.status, data.code);
                    err.data = data;
                    throw err;
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
                    const i18n = window.ATM.i18n;
                    const params = errorData.params || { error: errorData.error || '' };
                    const localizedMsg = (errorData.code && i18n ? i18n.t(errorData.code, params) : null)
                        || (errorData.error && i18n ? i18n.t(errorData.error, params) : null)
                        || errorData.error
                        || `HTTP Error: ${response.status}`;
                    const err = new BackendError(localizedMsg, response.status, errorData.code);
                    err.data = errorData;
                    throw err;
                }
                const resData = await response.json();
                if (resData.status === 'error') {
                    const i18n = window.ATM.i18n;
                    const params = resData.params || { error: resData.error || '' };
                    const localizedMsg = (resData.code && i18n ? i18n.t(resData.code, params) : null)
                        || (resData.error && i18n ? i18n.t(resData.error, params) : null)
                        || resData.error
                        || (i18n ? i18n.t('toast.server_error') : 'Server error');
                    const err = new BackendError(localizedMsg, response.status, resData.code);
                    err.data = resData;
                    throw err;
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

