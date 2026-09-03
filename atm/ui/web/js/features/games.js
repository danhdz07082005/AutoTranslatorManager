// --- atm/ui/web/js/features/games.js ---
// Architecture Rule 6: UI and DOM Manipulation ONLY. No Business Logic.
// Security Rule 8: Zero innerHTML, Zero inline handlers.

window.ATM = window.ATM || {};

window.ATM.Games = (function() {
    const containerId = 'games-container';
    let languages = {};
    
    // Poller Registry: 1 Game = 1 Poller
    const pollers = new Map(); // gameId -><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:middle"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg><span data-i18n="card.play">' + t('card.play', 'Play Game') + '</span>';
            btnStart.className = "btn-start flex-1 btn-action-start"; // We can add btn-success if it exists, otherwise just btn-start with inline style
            btnStart.style.backgroundColor = "var(--success)";
            btnStart.style.color = "white";
            btnStart.style.border = "none";
            btnStart.dataset.action = "play";
            progContainer.style.display = 'none';
            
            if (statusBadge) {
                statusBadge.setAttribute('data-i18n', 'status.completed');
                statusBadge.textContent = t('status.completed', 'Complete');
                statusBadge.style.backgroundColor = "rgba(16, 185, 129, 0.1)"; // success tinted
                statusBadge.style.color = "var(--success)";
            }
        }
        else if (state === 'INTERRUPTED') {
            btnStart.setAttribute('data-i18n', 'card.resume');
            btnStart.textContent = t('card.resume', 'Resume (Error/Restart)');
            btnStart.className = "btn-secondary flex-1 btn-action-start";
            btnStart.style.color = "var(--warning)";
            btnStart.style.backgroundColor = ""; // Reset if came from complete
            btnStart.dataset.action = "start";
            progContainer.style.display = 'block';
            if (progStatus) {
                progStatus.setAttribute('data-i18n', 'status.interrupted');
                progStatus.textContent = t('status.interrupted', 'Interrupted');
            }
            
            if (statusBadge) {
                statusBadge.setAttribute('data-i18n', 'status.interrupted');
                statusBadge.textContent = t('status.interrupted', 'Paused');
                statusBadge.style.backgroundColor = "rgba(245, 158, 11, 0.1)"; // warning tinted
                statusBadge.style.color = "var(--warning)";
            }
        }
    }

    // Start / Stop Logic
    async function handleStartStop(gameId, card) {
        const currentState = card.dataset.state;
        const btnStart = card.querySelector('[data-action="start"]');

        if (currentState === '') {
            // Stop
            btnStart.disabled = true;
            updateCardPartial(card, '');
            cleanupPoller(gameId); // Cleanup poller immediately
            await window.ATM.api.post('games/stop', { game_id: gameId }).catch(()=>{});
            btnStart.disabled = false;
        } else {
            // Start
            btnStart.disabled = true;
            updateCardPartial(card, '', 0);
            try {
                localStorage.removeItem('atm_needs_sync_' + gameId);
                const wsRefreshBtn = document.querySelector('.btn-refresh-workspace');
                if (wsRefreshBtn) wsRefreshBtn.classList.remove('btn-needs-sync');
                const dot = card.querySelector('.card-sync-dot');
                if (dot) dot.remove();
                
                const res = await window.ATM.api.post('games/start', { game_id: gameId });
                
                if (res.status === 'unicode_error') {
                    updateCardPartial(card, '');
                    const defaultMsg = window.ATM.i18n.t('games.auto_fix_confirm', "");
                    const msg = window.ATM.i18n ? window.ATM.i18n.t('games.unicode_error_msg', defaultMsg) : defaultMsg;
                    window.ATM.Modals.confirm(msg).then(async (agreed) => {
                        if (agreed) {
                            try {
                                const fixRes = await window.ATM.api.post('games/fix-path', { game_id: gameId });
                                if (fixRes.status === 'success') {
                                    const successMsg = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_success', '') : '';
                                    window.ATM.Toast.show(successMsg, "success");
                                    setTimeout(() => {
                                        const btn = card.querySelector('.btn-action-start');
                                        if (btn) btn.click();
                                    }, 1000);
                                } else {
                                    const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_error', '') : '';
                                    window.ATM.Toast.show(errorPrefix + (fixRes.error || 'Unknown error'), "error");
                                }
                            } catch (err) {
                                const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_error', '') : '';
                                window.ATM.Toast.show(errorPrefix + err.message, "error");
                            }
                        }
                    });
                    return;
                }
                
                startPoller(gameId, card);
            } catch(e) {
                updateCardPartial(card, '');
                if (window.ATM.Toast) {
                    const fallback = window.ATM.i18n ? (window.ATM.i18n.t('toast.start_failed') || 'Start failed') : 'Start failed';
                    window.ATM.Toast.show(e.message || fallback, "error");
                }
            } finally {
                btnStart.disabled = false;
            }
        }
    }

    // TASK 5: Polling Lifecycle (Stale-Response Protection, Cleanup)
    function startPoller(gameId, card) {
        cleanupPoller(gameId);
        
        const state = { isPolling: true, timer: null };
        pollers.set(gameId, state);

        const poll = async () => {
            if (!state.isPolling || card.dataset.state !== '') return;

            try {
                const status = await window.ATM.api.get(`games/translation-status?game_id=${gameId}`);
                
                if (!state.isPolling || card.dataset.state !== '') return;
                
                if (status.done) {
                    const isRealtimeFinished = (status.code === 'translation.realtime_finished');
                    const nextState = (status.error || isRealtimeFinished) ? '' : 'COMPLETE';
                    updateCardPartial(card, nextState);
                    if (status.error && window.ATM.Toast) {
                        const i18n = window.ATM.i18n;
                        const errMsg = (status.code && i18n ? i18n.t(status.code) : null)
                            || status.details
                            || (i18n ? i18n.t('status.failed') : null)
                            || 'Translation Failed';
                        window.ATM.Toast.show(errMsg, 'error');
                    }
                    cleanupPoller(gameId);
                    return;
                }
                
                const pct = (status.total > 0) ? (status.progress / status.total) * 100 : 0;
                updateCardPartial(card, '', pct);
                
                if (state.isPolling) {
                    state.timer = setTimeout(poll, 1000);
                }
                
            } catch(e) {
                console.error(`Polling network error for game ${gameId}:`, e);
                if (state.isPolling) {
                    state.timer = setTimeout(poll, 3000);
                }
            }
        };

        poll();
    }

    function cleanupPoller(gameId) {
        if (pollers.has(gameId)) {
            const state = pollers.get(gameId);
            state.isPolling = false;
            if (state.timer) clearTimeout(state.timer);
            pollers.delete(gameId);
        }
    }

    async function handlePlay(gameId) {
        try {
            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.initializing'), false);
            await window.ATM.api.post('games/play', { game_id: gameId }); 
        } catch(e) {
            if (window.ATM.Toast) {
                const fallback = window.ATM.i18n ? (window.ATM.i18n.t('toast.play_failed') || 'Play failed') : 'Play failed';
                window.ATM.Toast.show(e.message || fallback, "error");
            }
        }
    }

    // TASK 4: Local Mutation
    async function handleDelete(gameId, card) {
        const t = (key, fallback) => window.ATM.i18n ? (window.ATM.i18n.t(key) || fallback) : fallback;
        const msg = t('card.delete_confirm', "");
        if (!(await window.ATM.Modals.confirm(msg))) {
            return;
        }

        const btnDel = card.querySelector('[data-action="delete"]');
        if (btnDel) btnDel.disabled = true;

        try {
            await window.ATM.api.post('games/delete', { game_id: gameId });
            
            // Clean up poller to avoid zombie requests
            cleanupPoller(gameId);
            
            // Local mutation: Remove from DOM
            card.remove();
            
            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.delete_success'));
            
            // Check if empty
            const container = getContainer();
            if (container && container.children.length === 0) {
                renderEmptyState(container);
            }
        } catch(e) {
            if (btnDel) btnDel.disabled = false;
            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.delete_error'), true);
        }
    }
    
    // Refresh function for Add Game
    async function refreshLibrary() {
        await loadGames();
    }
    
    if (window.ATM.events) {
        window.ATM.events.subscribe('force_poller_restart', (data) => {
            const card = document.getElementById(`card-${data.gameId}`);
            if (card) {
                updateCardPartial(card, '', 0);
                startPoller(data.gameId, card);
            }
        });
    }

    return {
        init,
        loadGames,
        load: loadGames, // Alias for app.js
        refreshLibrary
    };
})();

