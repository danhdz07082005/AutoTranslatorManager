window.ATM = window.ATM || {};

window.ATM.Data = (function() {
    return {
        init: () => {
            const refreshBtn = document.getElementById('data-refresh-btn');
            if (refreshBtn) {
                refreshBtn.addEventListener('click', () => window.ATM.Data.refresh());
            }

            const btnClearCache = document.getElementById('data-keep-clear-btn');
            if (btnClearCache) {
                btnClearCache.addEventListener('click', () => {
                    const input = document.getElementById('cache-keep-count');
                    const keep = input ? parseInt(input.value) : 10;
                    window.ATM.api.post('data/clear', { type: 'cache', keep: keep })
                        .then(() => {
                            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.cache_cleared') || window.ATM.i18n.t('toast.cache_cleared'));
                            window.ATM.Data.refresh(true);
                        })
                        .catch(() => {
                            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.clear_cache_error'), true);
                        });
                });
            }

            const btnClearAllCache = document.getElementById('data-clear-all-cache-btn');
            if (btnClearAllCache) {
                btnClearAllCache.addEventListener('click', async () => {
                    const msg = window.ATM.i18n.t('data.clear_all_confirm') || 'Bạn có chắc chắn muốn xoá toàn bộ Cache?';
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'cache', keep: 0 })
                            .then(() => {
                                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.cache_cleared') || window.ATM.i18n.t('toast.cache_cleared'));
                                window.ATM.Data.refresh(true);
                            }).catch(() => {});
                    }
                });
            }

            const btnClearTM = document.getElementById('data-clear-tm-btn');
            if (btnClearTM) {
                btnClearTM.addEventListener('click', async () => {
                    const msg = window.ATM.i18n.t('data.clear_tm_confirm') || 'Xóa toàn bộ bộ nhớ dịch?';
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'tm' })
                            .then(() => {
                                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.tm_cleared') || window.ATM.i18n.t('toast.tm_cleared'));
                                window.ATM.Data.refresh(true);
                            }).catch(() => {});
                    }
                });
            }

            const btnOpenFolder = document.getElementById('data-open-folder-btn');
            if (btnOpenFolder) {
                btnOpenFolder.addEventListener('click', () => {
                    window.ATM.api.post('data/open_folder').catch(() => {});
                });
            }
        },

        refresh: async (silent = false) => {
            const cacheCount = document.getElementById('stat-cache-count');
            const cacheSize = document.getElementById('stat-cache-size');
            const tmCount = document.getElementById('stat-memory-count');
            const tmSize = document.getElementById('stat-memory-size');
            
            if (cacheCount) cacheCount.textContent = '';
            if (cacheSize) cacheSize.textContent = '';
            if (tmCount) tmCount.textContent = '';
            if (tmSize) tmSize.textContent = '';

            try {
                const res = await window.ATM.api.get('data/stats');
                const gc = res.global_cache || {};
                const gm = res.global_memory || {};

                if (cacheCount) cacheCount.textContent = String(gc.count || 0);
                if (cacheSize) cacheSize.textContent = ((gc.size_bytes || 0) / 1024).toFixed(1) + ' KB';
                if (tmCount) tmCount.textContent = String(gm.count || 0);
                if (tmSize) tmSize.textContent = ((gm.size_bytes || 0) / 1024).toFixed(1) + ' KB';

                if (!silent && window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.stats_refreshed') || 'Đã làm mới dữ liệu');
            } catch (e) {
                console.error('Data stats error:', e);
                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.stats_error'), true);
            }
        }
    };
})();

