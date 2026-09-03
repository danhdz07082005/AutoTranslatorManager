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
                            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.cache_cleared') || '', 'success');
                            window.ATM.Data.refresh(true);
                        })
                        .catch((err) => {
                            if (window.ATM.Toast) window.ATM.Toast.show(err.message || window.ATM.i18n.t('toast.clear_cache_error', 'Error clearing cache'), 'error');
                        });
                });
            }

            const btnClearAllCache = document.getElementById('data-clear-all-cache-btn');
            if (btnClearAllCache) {
                btnClearAllCache.addEventListener('click', async () => {
                    const msg = window.ATM.i18n.t('data.clear_all_confirm') || window.ATM.i18n.t('data.clear_all_confirm', '');
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'cache', keep: 0 })
                            .then(() => {
                                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.cache_cleared') || '', 'success');
                                window.ATM.Data.refresh(true);
                            }).catch((err) => {
                                if (window.ATM.Toast) window.ATM.Toast.show(err.message || window.ATM.i18n.t('toast.clear_cache_error_all', 'Error clearing all cache'), 'error');
                            });
                    }
                });
            }

            const btnClearTM = document.getElementById('data-clear-tm-btn');
            if (btnClearTM) {
                btnClearTM.addEventListener('click', async () => {
                    const msg = window.ATM.i18n.t('data.clear_tm_confirm') || window.ATM.i18n.t('data.clear_tm_confirm', 'Clear all translation memory?');
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'tm' })
                            .then(() => {
                                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.tm_cleared') || '', 'success');
                                window.ATM.Data.refresh(true);
                            }).catch((err) => {
                                if (window.ATM.Toast) window.ATM.Toast.show(err.message || window.ATM.i18n.t('toast.tm_error', 'Error clearing TM'), 'error');
                            });
                    }
                });
            }

            const btnOpenFolder = document.getElementById('data-open-folder-btn');
            if (btnOpenFolder) {
                btnOpenFolder.addEventListener('click', () => {
                    window.ATM.api.post('data/open_folder').catch((err) => {
                        if (window.ATM.Toast) window.ATM.Toast.show(err.message || window.ATM.i18n.t('toast.folder_error', 'Error opening folder'), 'error');
                    });
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

                const listContainer = document.getElementById('game-data-list');
                if (listContainer) {
                    listContainer.innerHTML = '';
                    if (!res.games || res.games.length === 0) {
                        listContainer.innerHTML = ``;
                    } else {
                        res.games.forEach(g => {
                            const sizeKb = ((g.entries || 0) * 150 / 1024).toFixed(1); // Approximate 150 bytes per row
                            const row = document.createElement('div');
                            row.className = 'data-card';
                            row.style.display = 'flex';
                            row.style.alignItems = 'center';
                            row.style.justifyContent = 'space-between';
                            row.style.padding = '10px';
                            row.style.marginBottom = '10px';
                            
                            const nameText = window.ATM.i18n ? window.ATM.i18n.t('data.game_name', '') : '';
                            const folderText = window.ATM.i18n ? window.ATM.i18n.t('data.folder', '') : '';
                            const entriesText = window.ATM.i18n ? window.ATM.i18n.t('data.entries_count', '') : '';
                            const sizeText = window.ATM.i18n ? window.ATM.i18n.t('data.approx_size', '') : '';
                            
                            row.innerHTML = `
                                <div>
                                    <div style="font-weight: bold; margin-bottom: 4px;">${nameText}${g.name} <span class="engine-badge">${g.engine}</span></div>
                                    <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 4px;">${folderText}${g.folder}</div>
                                    <div style="font-size: 12px; color: var(--text-secondary);">${entriesText}<strong>${g.entries}</strong> | ${sizeText}<strong>${sizeKb} KB</strong></div>
                                </div>
                                <div style="display: flex; gap: 8px;">
                                    <button class="btn-secondary btn-clear-keep" data-id="${g.id}"></button>
                                    <button class="btn-delete btn-clear-all" data-id="${g.id}"></button>
                                </div>
                            `;
                            listContainer.appendChild(row);
                        });
                        
                        listContainer.querySelectorAll('.btn-clear-all').forEach(btn => {
                            btn.addEventListener('click', async (e) => {
                                const gameId = e.target.getAttribute('data-id');
                                const confirmMsg = window.ATM.i18n ? window.ATM.i18n.t('data.clear_game_confirm', '') : '';
                                if (await window.ATM.Modals.confirm(confirmMsg)) {
                                    window.ATM.api.post('data/clear', { type: 'game_lines', game_id: gameId, keep: 0 })
                                        .then(() => {
                                            const successMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.game_cleared', window.ATM.i18n.t('toast.game_cleared', 'Game data cleared successfully.')) : window.ATM.i18n.t('toast.game_cleared', 'Game data cleared successfully.');
                                            window.ATM.Toast.show(successMsg, 'success');
                                            window.ATM.Data.refresh(true);
                                        }).catch(err => {
                                            const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_error', window.ATM.i18n.t('toast.clear_error', 'Clear error: ')) : window.ATM.i18n.t('toast.clear_error', 'Clear error: ');
                                            window.ATM.Toast.show(errorPrefix + (err.message || 'Error'), 'error');
                                        });
                                }
                            });
                        });
                        
                        listContainer.querySelectorAll('.btn-clear-keep').forEach(btn => {
                            btn.addEventListener('click', async (e) => {
                                const gameId = e.target.getAttribute('data-id');
                                const promptMsg = window.ATM.i18n ? window.ATM.i18n.t('data.keep_prompt', '') : '';
                                const input = prompt(promptMsg, "5000");
                                if (input !== null) {
                                    const keepCount = parseInt(input, 10);
                                    if (isNaN(keepCount) || keepCount < 0) {
                                        window.ATM.Toast.show(window.ATM.i18n.t('toast.invalid_number', 'Please enter a valid number.'), "error");
                                        return;
                                    }
                                    window.ATM.api.post('data/clear', { type: 'game_lines', game_id: gameId, keep: keepCount })
                                        .then(() => {
                                            const successMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.game_cleared', window.ATM.i18n.t('toast.game_cleared', 'Game data cleared successfully.')) : window.ATM.i18n.t('toast.game_cleared', 'Game data cleared successfully.');
                                            window.ATM.Toast.show(successMsg, 'success');
                                            window.ATM.Data.refresh(true);
                                        }).catch(err => {
                                            const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_error', window.ATM.i18n.t('toast.clear_error', 'Clear error: ')) : window.ATM.i18n.t('toast.clear_error', 'Clear error: ');
                                            window.ATM.Toast.show(errorPrefix + (err.message || 'Error'), 'error');
                                        });
                                }
                            });
                        });
                        
                        if (window.ATM.i18n) window.ATM.i18n.translateDOM(listContainer);
                    }
                }

                if (!silent && window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.stats_refreshed') || '');
            } catch (e) {
                console.error('Data stats error:', e);
                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.stats_error') || window.ATM.i18n.t('toast.stats_error', 'Error loading stats'), 'error');
            }
        }
    };
})();
