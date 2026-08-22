window.ATM = window.ATM || {};

/**
 * ATM.api - Core Fetch Wrapper
 * Đảm bảo Timeout, Parse JSON tự động, và cung cấp AbortController.
 */
(function() {
    const DEFAULT_TIMEOUT = 10000; // 10 giây mặc định

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
        const id = setTimeout(() => controller.abort(), timeout);

        const response = await fetch(resource, {
            ...options,
            signal: controller.signal  
        });
        
        clearTimeout(id);
        return response;
    }

    window.ATM.api = {
        NetworkError,
        BackendError,
        
        async get(endpoint, options = {}) {
            try {
                const response = await fetchWithTimeout(`/api/${endpoint}`, options);
                if (!response.ok) {
                    throw new BackendError(`HTTP Error: ${response.status}`, response.status);
                }
                return await response.json();
            } catch (error) {
                if (error.name === 'AbortError') {
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
                return await response.json();
            } catch (error) {
                if (error.name === 'AbortError') {
                    throw new NetworkError("Request timed out.");
                }
                throw error;
            }
        }
    };
})();
",



