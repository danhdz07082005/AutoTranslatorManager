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
                    const rawVal = input ? parseInt(input.value, 10) : 10;
                    const keep = (isNaN(rawVal) || rawVal < 0) ? 10 : rawVal;
                    window.ATM.api.post('data/clear', { type: 'cache', keep: keep })
                        .then(() => {
                            const clearedMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.cache_cleared', 'Cache cleared successfully.') : 'Cache cleared successfully.';
                            if (window.ATM.Toast) window.ATM.Toast.show(clearedMsg, 'success');
                            window.ATM.Data.refresh(true);
                        })
                        .catch((err) => {
                            const clearErr = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_cache_error', 'Error clearing cache') : 'Error clearing cache';
                            if (window.ATM.Toast) window.ATM.Toast.show(err.message || clearErr, 'error');
                        });
                });
            }

            const btnClearAllCache = document.getElementById('data-clear-all-cache-btn');
            if (btnClearAllCache) {
                btnClearAllCache.addEventListener('click', async () => {
                    const msg = window.ATM.i18n ? window.ATM.i18n.t('data.clear_all_confirm', 'Are you sure you want to clear all cache?') : 'Are you sure you want to clear all cache?';
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'cache', keep: 0 })
                            .then(() => {
                                const clearedMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.cache_cleared', 'Cache cleared successfully.') : 'Cache cleared successfully.';
                                if (window.ATM.Toast) window.ATM.Toast.show(clearedMsg, 'success');
                                if (window.ATM.events) {
                                    window.ATM.events.publish('cache:cleared', {});
                                    window.ATM.events.publish('cache:synced', {});
                                }
                                window.ATM.Data.refresh(true);
                            }).catch((err) => {
                                const clearErrAll = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_cache_error_all', 'Error clearing all cache') : 'Error clearing all cache';
                                if (window.ATM.Toast) window.ATM.Toast.show(err.message || clearErrAll, 'error');
                            });
                    }
                });
            }

            const btnClearTM = document.getElementById('data-clear-tm-btn');
            if (btnClearTM) {
                btnClearTM.addEventListener('click', async () => {
                    const msg = window.ATM.i18n ? window.ATM.i18n.t('data.clear_tm_confirm', 'Clear all translation memory?') : 'Clear all translation memory?';
                    if (await window.ATM.Modals.confirm(msg)) {
                        window.ATM.api.post('data/clear', { type: 'tm' })
                            .then(() => {
                                const tmClearedMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.tm_cleared', 'Translation memory cleared.') : 'Translation memory cleared.';
                                if (window.ATM.Toast) window.ATM.Toast.show(tmClearedMsg, 'success');
                                if (window.ATM.events) {
                                    window.ATM.events.publish('glossary:changed', {});
                                }
                                window.ATM.Data.refresh(true);
                            }).catch((err) => {
                                const tmErr = window.ATM.i18n ? window.ATM.i18n.t('toast.tm_error', 'Error clearing TM') : 'Error clearing TM';
                                if (window.ATM.Toast) window.ATM.Toast.show(err.message || tmErr, 'error');
                            });
                    }
                });
            }

            const btnOpenFolder = document.getElementById('data-open-folder-btn');
            if (btnOpenFolder) {
                btnOpenFolder.addEventListener('click', () => {
                    window.ATM.api.post('data/open_folder').catch((err) => {
                        const folderErr = window.ATM.i18n ? window.ATM.i18n.t('toast.folder_error', 'Error opening folder') : 'Error opening folder';
                        if (window.ATM.Toast) window.ATM.Toast.show(err.message || folderErr, 'error');
                    });
                });
            }
            if (window.ATM.events) {
                window.ATM.events.subscribe('lang:changed', () => {
                    window.ATM.Data.refresh(true);
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
                    listContainer.textContent = '';
                    if (!res.games || res.games.length === 0) {
                        const emptyDiv = document.createElement('div');
                        emptyDiv.className = 'text-secondary';
                        emptyDiv.style.padding = '10px';
                        emptyDiv.setAttribute('data-i18n', 'data.no_games');
                        emptyDiv.textContent = window.ATM.i18n ? window.ATM.i18n.t('data.no_games', 'No game data found.') : 'No game data found.';
                        listContainer.appendChild(emptyDiv);
                    } else {
                        res.games.forEach(g => {
                            const sizeKb = g.size_kb !== undefined ? Number(g.size_kb).toFixed(1) : ((g.entries || 0) * 150 / 1024).toFixed(1);
                            const row = document.createElement('div');
                            row.className = 'data-card';
                            row.style.display = 'flex';
                            row.style.alignItems = 'center';
                            row.style.justifyContent = 'space-between';
                            row.style.padding = '10px';
                            row.style.marginBottom = '10px';
                            
                            const nameText = window.ATM.i18n ? window.ATM.i18n.t('data.game_name', 'Tên Game: ') : 'Tên Game: ';
                            const folderText = window.ATM.i18n ? window.ATM.i18n.t('data.folder', 'Thư mục: ') : 'Thư mục: ';
                            const entriesText = window.ATM.i18n ? window.ATM.i18n.t('data.entries_count', 'Số câu: ') : 'Số câu: ';
                            const termsText = window.ATM.i18n ? window.ATM.i18n.t('data.terms_count', 'Thuật ngữ: ') : 'Thuật ngữ: ';
                            const sizeText = window.ATM.i18n ? window.ATM.i18n.t('data.size_display', 'Kích thước (Size): ') : 'Kích thước (Size): ';
                            
                            const infoDiv = document.createElement('div');

                            const titleDiv = document.createElement('div');
                            titleDiv.style.fontWeight = 'bold';
                            titleDiv.style.marginBottom = '4px';
                            titleDiv.textContent = `${nameText}${g.name || ''} `;

                            const engineBadge = document.createElement('span');
                            engineBadge.className = 'engine-badge';
                            engineBadge.setAttribute('data-engine', g.engine || '');
                            engineBadge.textContent = g.engine === 'Bakin' ? 'Bakin (BETA)' : (g.engine || '');
                            titleDiv.appendChild(engineBadge);

                            const folderDiv = document.createElement('div');
                            folderDiv.style.fontSize = '12px';
                            folderDiv.style.color = 'var(--text-secondary)';
                            folderDiv.style.marginBottom = '4px';
                            folderDiv.textContent = `${folderText}${g.folder || ''}`;

                            const statsDiv = document.createElement('div');
                            statsDiv.style.fontSize = '12px';
                            statsDiv.style.color = 'var(--text-secondary)';

                            const entriesSpan = document.createElement('span');
                            entriesSpan.textContent = entriesText;
                            const entriesStrong = document.createElement('strong');
                            entriesStrong.textContent = String(g.entries || 0);

                            const sep1 = document.createTextNode(' | ');

                            const termsSpan = document.createElement('span');
                            termsSpan.textContent = termsText;
                            const termsStrong = document.createElement('strong');
                            termsStrong.textContent = String(g.terms || 0);

                            const sep2 = document.createTextNode(' | ');

                            const sizeSpan = document.createElement('span');
                            sizeSpan.textContent = sizeText;
                            const sizeStrong = document.createElement('strong');
                            sizeStrong.textContent = `${sizeKb} KB`;

                            statsDiv.appendChild(entriesSpan);
                            statsDiv.appendChild(entriesStrong);
                            statsDiv.appendChild(sep1);
                            statsDiv.appendChild(termsSpan);
                            statsDiv.appendChild(termsStrong);
                            statsDiv.appendChild(sep2);
                            statsDiv.appendChild(sizeSpan);
                            statsDiv.appendChild(sizeStrong);

                            infoDiv.appendChild(titleDiv);
                            infoDiv.appendChild(folderDiv);
                            infoDiv.appendChild(statsDiv);

                            const actionsDiv = document.createElement('div');
                            actionsDiv.style.display = 'flex';
                            actionsDiv.style.gap = '8px';

                            const btnKeep = document.createElement('button');
                            btnKeep.className = 'btn-secondary btn-clear-keep';
                            btnKeep.setAttribute('data-id', g.id);
                            btnKeep.title = window.ATM.i18n ? (window.ATM.i18n.t('data.keep_clear') || 'Clear & Keep N') : 'Clear & Keep';
                            btnKeep.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>';

                            const btnClearAll = document.createElement('button');
                            btnClearAll.className = 'btn-delete btn-clear-all';
                            btnClearAll.setAttribute('data-id', g.id);
                            btnClearAll.title = window.ATM.i18n ? (window.ATM.i18n.t('data.clear_all') || 'Clear All') : 'Clear All';
                            btnClearAll.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>';

                            actionsDiv.appendChild(btnKeep);
                            actionsDiv.appendChild(btnClearAll);

                            row.appendChild(infoDiv);
                            row.appendChild(actionsDiv);
                            listContainer.appendChild(row);
                        });
                        
                        listContainer.querySelectorAll('.btn-clear-all').forEach(btn => {
                            btn.addEventListener('click', async (e) => {
                                const gameId = e.currentTarget.getAttribute('data-id');
                                const msg = window.ATM.i18n ? window.ATM.i18n.t('data.clear_game_confirm', 'Are you sure you want to clear this game data?') : 'Are you sure you want to clear this game data?';
                                const agreed = await window.ATM.Modals.confirm(msg);
                                if (agreed) {
                                    try {
                                        const res = await window.ATM.api.post('data/clear', { type: 'game_all', game_id: gameId });
                                        if (res.status === 'success') {
                                            const clearedMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_game_success', 'Cleared') : 'Cleared';
                                            if (window.ATM.Toast) window.ATM.Toast.show(clearedMsg, "success");
                                            if (window.ATM.events) {
                                                window.ATM.events.publish('glossary:changed', { gameId: gameId });
                                                window.ATM.events.publish('cache:updated', { gameId: gameId });
                                                window.ATM.events.publish('editor:reload', { gameId: gameId });
                                            }
                                            window.ATM.Data.refresh(true);
                                        }
                                    } catch (err) {
                                        console.error(err);
                                        const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_error', 'Clear error: ') : 'Clear error: ';
                                        if (window.ATM.Toast) window.ATM.Toast.show(errorPrefix + (err.message || 'Error'), 'error');
                                    }
                                }
                            });
                        });
                        
                        listContainer.querySelectorAll('.btn-clear-keep').forEach(btn => {
                            btn.addEventListener('click', async (e) => {
                                const gameId = e.currentTarget.getAttribute('data-id');
                                const promptMsg = window.ATM.i18n ? window.ATM.i18n.t('data.keep_prompt', '') : '';
                                const input = await window.ATM.Modals.prompt(promptMsg, "5000");
                                if (input !== null && input !== "") {
                                    const keepCount = parseInt(input, 10);
                                    if (isNaN(keepCount) || keepCount < 0) {
                                        const invalidNumMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.invalid_number', 'Please enter a valid number.') : 'Please enter a valid number.';
                                        if (window.ATM.Toast) window.ATM.Toast.show(invalidNumMsg, "error");
                                        return;
                                    }
                                    window.ATM.api.post('data/clear', { type: 'game_lines', game_id: gameId, keep: keepCount })
                                        .then(() => {
                                            const successMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.game_cleared', 'Game data cleared successfully.') : 'Game data cleared successfully.';
                                            if (window.ATM.Toast) window.ATM.Toast.show(successMsg, 'success');
                                            if (window.ATM.events) {
                                                window.ATM.events.publish('cache:updated', { gameId: gameId });
                                                window.ATM.events.publish('editor:reload', { gameId: gameId });
                                            }
                                            window.ATM.Data.refresh(true);
                                        }).catch(err => {
                                            const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('toast.clear_error', 'Clear error: ') : 'Clear error: ';
                                            if (window.ATM.Toast) window.ATM.Toast.show(errorPrefix + (err.message || 'Error'), 'error');
                                        });
                                }
                            });
                        });
                        
                        if (window.ATM.i18n) window.ATM.i18n.updateDOM();
                    }
                }

                if (!silent && window.ATM.Toast) {
                    const refreshedMsg = window.ATM.i18n ? (window.ATM.i18n.t('toast.stats_refreshed') || '') : '';
                    if (refreshedMsg) window.ATM.Toast.show(refreshedMsg);
                }
            } catch (e) {
                console.error('Data stats error:', e);
                const statsErrMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.stats_error', 'Error loading stats') : 'Error loading stats';
                if (window.ATM.Toast) window.ATM.Toast.show(statsErrMsg, 'error');
            }
        }
    };
})();
