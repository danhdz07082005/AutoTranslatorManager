// --- atm/ui/web/js/features/games.js ---
// Architecture Rule 6: UI and DOM Manipulation ONLY. No Business Logic.
// Security Rule 8: Zero innerHTML, Zero inline handlers.

window.ATM = window.ATM || {};

window.ATM.Games = (function() {
    const containerId = 'games-container';
    let languages = {};
    
    // Poller Registry: 1 Game = 1 Poller
    const pollers = new Map(); // gameId -> timeoutId

    const getContainer = () => document.getElementById(containerId);

    // Initializer
    async function init() {
        languages = await window.ATM.api.get('languages') || {};
        setupEventDelegation();
        setupCrossTabSync();
        await loadGames();
    }
    
    function updateCardSyncState(gameId, needsSync) {
        const card = document.getElementById(`card-${gameId}`);
        if (!card) return;
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;
        const btnStart = card.querySelector('.btn-action-start');

        if (needsSync) {
            if (btnStart && card.dataset.state !== 'TRANSLATING') {
                btnStart.classList.remove('btn-start', 'btn-success', 'btn-secondary');
                btnStart.classList.add('btn-delete', 'heartbeat-neon-red');
                btnStart.textContent = t('games.btn_sync', 'Đồng bộ & Dịch');
                btnStart.removeAttribute('data-i18n');
            }
        } else {
            if (btnStart) {
                btnStart.classList.remove('heartbeat-neon-red');
                updateCardPartial(card, card.dataset.state, 0);
            }
        }
    }

    function refreshAllCardsSyncState() {
        const container = getContainer();
        if (!container) return;
        const cards = container.querySelectorAll('.game-card');
        cards.forEach(card => {
            const gameId = card.dataset.gameId;
            if (!gameId) return;
            const needsSync = localStorage.getItem('atm_needs_sync_' + gameId) === 'true';
            updateCardSyncState(gameId, needsSync);
        });
    }

    // Cross-tab synchronization for the 'Sync' heartbeat
    function setupCrossTabSync() {
        window.ATM.events.subscribe('glossary:changed', (payload) => {
            if (payload && payload.gameId) {
                updateCardSyncState(payload.gameId, true);
            }
        });
        window.ATM.events.subscribe('cache:updated', (payload) => {
            if (payload && payload.gameId) {
                updateCardSyncState(payload.gameId, true);
            }
        });
        window.ATM.events.subscribe('cache:synced', (payload) => {
            if (payload && payload.gameId) {
                updateCardSyncState(payload.gameId, false);
            }
        });
        window.ATM.events.subscribe('cache:cleared', () => {
            refreshAllCardsSyncState();
        });
        window.addEventListener('storage', (e) => {
            if (e.key && e.key.startsWith('atm_needs_sync_')) {
                const gameId = e.key.replace('atm_needs_sync_', '');
                updateCardSyncState(gameId, e.newValue === 'true');
            }
        });
    }

    // TASK 4: Event Delegation - One listener to rule them all
    function setupEventDelegation() {
        const btnAdd = document.getElementById('add-game-btn');
        if (btnAdd) {
            btnAdd.addEventListener('click', async () => {
                btnAdd.disabled = true;
                try {
                    const res = await window.ATM.api.post('games/add', {}, { timeout: 300000 });
                    if (res && res.status === 'success' && res.game) {
                        appendGameCard(res.game);
                        
                        const container = getContainer();
                        const empty = container.querySelector('.empty-state');
                        if (empty) empty.remove();
                        const msg = window.ATM.i18n ? window.ATM.i18n.t('toast.add_game_success') || window.ATM.i18n.t('toast.add_game_success') : window.ATM.i18n.t('toast.add_game_success');
                        if (window.ATM.Toast) window.ATM.Toast.show(msg, "success");
                    } else if (res && res.status === 'cancelled') {
                        // User cancelled the file dialog  no action needed
                    } else if (res && res.error) {
                        const isDup = (res.code === 'toast.duplicate_game') || res.error.includes("thêm vào hệ thống") || res.error.includes("already exists");
                        const msg = isDup && window.ATM.i18n ? window.ATM.i18n.t('toast.duplicate_game') : res.error;
                        if (window.ATM.Toast) window.ATM.Toast.show(msg, "error");
                    }
                } catch(e) {
                    console.error("Failed to add game:", e);
                    const i18n = window.ATM.i18n;
                    const isDup = (e.code === 'toast.duplicate_game')
                        || (e.data && e.data.code === 'toast.duplicate_game')
                        || (e.message && (e.message.includes("already exists") || e.message.includes("thêm vào hệ thống")));
                    const msg = isDup && i18n ? i18n.t('toast.duplicate_game') : (e.message || (i18n ? i18n.t('toast.add_game_error') : 'Add game error'));
                    if (window.ATM.Toast) window.ATM.Toast.show(msg, "error");
                } finally {
                    btnAdd.disabled = false;
                }
            });
        }

        const container = getContainer();
        if (!container) return;

        container.addEventListener('click', async (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            
            const card = btn.closest('.game-card');
            if (!card) return;
            
            const gameId = card.dataset.gameId;
            const action = btn.dataset.action;

            // Handle Action Start/Pause
            if (action === 'start') {
                handleStartStop(gameId, card);
            } else if (action === 'play') {
                handlePlay(gameId);
            } else if (action === 'delete') {
                handleDelete(gameId, card);
            } else if (action === 'glossary' || action === 'tm' || action === 'editor') {
                // Tier 2 Architecture: Route all deep edits to the Workspace
                if (window.ATM.Workspace) {
                    window.ATM.Workspace.open(gameId);
                }
            }
        });

        // Event delegation for select boxes (Config changes)
        container.addEventListener('change', (e) => {
            if (e.target.matches('.engine-select, .source-select, .target-select')) {
                const card = e.target.closest('.game-card');
                if (!card) return;
                
                const gameId = card.dataset.gameId;
                const engine = card.querySelector('.engine-select').value;
                const source = card.querySelector('.source-select').value;
                const target = card.querySelector('.target-select').value;
                
                window.ATM.api.post('games/update-settings', {
                    game_id: gameId,
                    translator: engine,
                    input_lang: source,
                    output_lang: target
                }).catch(err => console.error("Error saving settings:", err));
            }
        });
    }

    function createGameCard(game) {
        const template = document.getElementById('game-card-template');
        if (!template) return null;

        const langArr = Object.keys(languages).map(k => ({value: k, text: languages[k]}));
        const clone = template.content.cloneNode(true);
        const card = clone.querySelector('.game-card');
        
        // Set dataset ID
        card.id = `card-${game.id}`;
        card.dataset.gameId = game.id;
        card.dataset.state = game.runtime_state || 'READY';
        
        // Sync Button
        const needsSync = localStorage.getItem('atm_needs_sync_' + String(game.id)) === 'true';
        if (needsSync) {
            const btnStart = card.querySelector('.btn-action-start');
            if (btnStart) {
                btnStart.classList.remove('btn-start', 'btn-success', 'btn-secondary');
                btnStart.classList.add('btn-delete', 'heartbeat-neon-red');
                btnStart.removeAttribute('data-i18n');
                btnStart.textContent = window.ATM.i18n ? window.ATM.i18n.t('games.btn_sync', 'Đồng bộ & Dịch') : 'Đồng bộ & Dịch';
            }
        }
        
        // Anti-XSS: textContent ONLY
        const gameName = game.game_name || 'Unknown';
        card.querySelector('.game-name').textContent = gameName;
        card.querySelector('.game-path').textContent = game.exe_path || '';
        const badgeEl = card.querySelector('.engine-badge');
        if (badgeEl) {
            badgeEl.textContent = game.engine || 'Unknown';
            badgeEl.dataset.engine = game.engine || 'Unknown';
        }
        
        // Avatar
        const avatar = card.querySelector('.game-avatar');
        if (avatar) {
            avatar.textContent = gameName.charAt(0).toUpperCase();
        }

        // Build Selectors
        const engineSel = card.querySelector('.engine-select');
        buildOptions(engineSel, [{value: 'google', text: 'Google Translate'}, {value: 'deepl', text: 'DeepL API'}], game.translator);

        const srcSel = card.querySelector('.source-select');
        buildOptions(srcSel, langArr, game.input_lang, false);

        const tgtSel = card.querySelector('.target-select');
        buildOptions(tgtSel, langArr, game.output_lang, true);

        return clone;
    }

    function appendGameCard(game) {
        const container = getContainer();
        if (!container) return;
        
        const clone = createGameCard(game);
        if (clone) {
            container.appendChild(clone);
            const card = document.getElementById(`card-${game.id}`);
            if (card) {
                updateCardPartial(card, card.dataset.state, 0);
            }
            if (window.ATM.i18n && typeof window.ATM.i18n.updateDOM === 'function') {
                window.ATM.i18n.updateDOM();
            }
        }
    }

    // TASK 3: Render Transaction using DocumentFragment and replaceChildren
    async function loadGames() {
        const container = getContainer();
        if (!container) return;

        try {
            const data = await window.ATM.api.get('games');
            const games = data.games || [];
            
            if (games.length === 0) {
                renderEmptyState(container);
                return;
            }

            const template = document.getElementById('game-card-template');
            if (!template) {
                console.error("Missing game-card-template in HTML");
                return;
            }

            const fragment = document.createDocumentFragment();
            const langArr = Object.keys(languages).map(k => ({value: k, text: languages[k]}));

            games.forEach(game => {
                const clone = createGameCard(game);
                if (clone) fragment.appendChild(clone);
            });

            // Commit Transaction - single DOM manipulation
            container.replaceChildren(fragment);

            // Re-apply states and start pollers if needed
            games.forEach(game => {
                const card = document.getElementById(`card-${game.id}`);
                if (card) {
                    const pct = game.runtime_total ? Math.round((game.runtime_progress / game.runtime_total) * 100) : 0;
                    updateCardPartial(card, card.dataset.state, pct);
                    
                    if (card.dataset.state === 'TRANSLATING') {
                        startPoller(game.id, card);
                    }
                }
            });

            // Update i18n
            if (window.ATM.i18n && window.ATM.i18n.updateDOM) window.ATM.i18n.updateDOM();

        } catch (e) {
            console.error("Failed to load games:", e);
            renderErrorState(container, e.message || 'Network Timeout');
        }
    }

    function buildOptions(select, opts, selected, excludeAuto = false) {
        select.textContent = ''; // Clear options
        opts.forEach(opt => {
            if (excludeAuto && opt.value === 'auto') return;
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.text;
            if (opt.value === selected) option.selected = true;
            select.appendChild(option);
        });
    }

    function renderEmptyState(container) {
        const div = document.createElement('div');
        div.className = 'empty-state';
        div.style.textAlign = 'center';
        div.style.padding = '40px';
        const h3 = document.createElement('h3');
        h3.dataset.i18n = 'dashboard.empty_title';
        h3.textContent = window.ATM.i18n ? (window.ATM.i18n.t('dashboard.empty_title') || window.ATM.i18n.t('dashboard.empty_title')) : window.ATM.i18n.t('dashboard.empty_title');
        const p = document.createElement('p');
        p.dataset.i18n = 'dashboard.empty_desc';
        p.textContent = window.ATM.i18n ? (window.ATM.i18n.t('dashboard.empty_desc') || window.ATM.i18n.t('dashboard.empty_desc')) : window.ATM.i18n.t('dashboard.empty_desc');
        div.appendChild(h3);
        div.appendChild(p);
        container.replaceChildren(div);
    }

    function renderErrorState(container, errorMsg = '') {
        const div = document.createElement('div');
        div.className = 'empty-state';
        div.style.textAlign = 'center';
        div.style.padding = '40px';
        const h3 = document.createElement('h3');
        h3.textContent = window.ATM.i18n.t('toast.connection_error');
        const p = document.createElement('p');
        p.textContent = errorMsg;
        p.style.color = 'var(--text-muted)';
        div.appendChild(h3);
        div.appendChild(p);
        container.replaceChildren(div);
    }

    // TASK 5: Partial UI update - Never recreate the card
    function updateCardPartial(card, state, percent = 0) {
        card.dataset.state = state;
        
        const btnStart = card.querySelector('.btn-action-start');
        const progContainer = card.querySelector('.progress-container');
        const progBarFill = card.querySelector('.progress-bar-fill');
        const progPercent = card.querySelector('.progress-percent');
        const progStatus = card.querySelector('.progress-status');
        const statusBadge = card.querySelector('.status-badge');

        if (!btnStart) return;
        
        // Helper rút gọn
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;

        if (state === 'READY') {
            btnStart.setAttribute('data-i18n', 'card.start');
            btnStart.textContent = t('card.start', 'Bắt đầu dịch');
            btnStart.className = "btn-start flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'none';
            if (statusBadge) {
                statusBadge.textContent = t('status.ready', 'Sẵn sàng');
                statusBadge.style.backgroundColor = "var(--bg-hover)";
                statusBadge.style.color = "var(--text-muted)";
            }
            
            const needsSync = localStorage.getItem('atm_needs_sync_' + card.dataset.gameId) === 'true';
            if (needsSync) {
                btnStart.classList.remove('btn-start');
                btnStart.classList.add('btn-delete', 'heartbeat-neon-red');
                btnStart.textContent = t('games.btn_sync', 'Đồng bộ & Dịch');
                btnStart.removeAttribute('data-i18n');
            }
        } 
        else if (state === 'TRANSLATING') {
            btnStart.removeAttribute('data-i18n');
            btnStart.textContent = t('card.stop', 'Dừng');
            btnStart.className = "btn-delete flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'block';
            
            if (progBarFill) progBarFill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
            if (progPercent) progPercent.textContent = `${Math.round(percent)}%`;
            if (progStatus) progStatus.textContent = t('card.translating', 'Đang dịch...');
            
            if (statusBadge) {
                statusBadge.textContent = t('status.running', 'Đang dịch...');
                statusBadge.style.backgroundColor = "rgba(59, 130, 246, 0.1)"; // accent tinted
                statusBadge.style.color = "var(--accent)";
            }
        }
        else if (state === 'COMPLETE') {
            btnStart.removeAttribute('data-i18n');
            btnStart.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:6px;vertical-align:middle"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>' + t('card.play', 'Chơi Game');
            btnStart.className = "btn-success flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "play";
            progContainer.style.display = 'none';
            
            if (statusBadge) {
                statusBadge.textContent = t('status.completed', 'Hoàn thành');
                statusBadge.style.backgroundColor = "rgba(16, 185, 129, 0.1)"; // success tinted
                statusBadge.style.color = "var(--success)";
            }
            
            const needsSync = localStorage.getItem('atm_needs_sync_' + card.dataset.gameId) === 'true';
            if (needsSync) {
                btnStart.classList.remove('btn-success');
                btnStart.classList.add('btn-delete', 'heartbeat-neon-red');
                btnStart.textContent = t('games.btn_sync', 'Đồng bộ & Dịch');
                btnStart.removeAttribute('data-i18n');
                btnStart.dataset.action = "start";
            }
        }
        else if (state === 'INTERRUPTED') {
            btnStart.removeAttribute('data-i18n');
            btnStart.textContent = t('card.resume', 'Tiếp tục');
            btnStart.className = "btn-warning flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'block';
            if (progStatus) progStatus.textContent = t('status.paused', 'Tạm dừng');
            
            if (statusBadge) {
                statusBadge.textContent = t('status.paused', 'Tạm dừng');
                statusBadge.style.backgroundColor = "rgba(245, 158, 11, 0.1)"; // warning tinted
                statusBadge.style.color = "var(--warning)";
            }
            
            const needsSync = localStorage.getItem('atm_needs_sync_' + card.dataset.gameId) === 'true';
            if (needsSync) {
                btnStart.classList.remove('btn-warning');
                btnStart.classList.add('btn-delete', 'heartbeat-neon-red');
                btnStart.textContent = t('games.btn_sync', 'Đồng bộ & Dịch');
                btnStart.removeAttribute('data-i18n');
                btnStart.dataset.action = "start";
            }
        }
        else {
            // Fallback for unknown states
            btnStart.removeAttribute('data-i18n');
            btnStart.textContent = state;
            btnStart.className = "btn-secondary flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'none';
        }
    }

    // Start / Stop Logic
    async function handleStartStop(gameId, card) {
        const currentState = card.dataset.state;
        const btnStart = card.querySelector('[data-action="start"]');

        if (currentState === 'TRANSLATING') {
            // Stop
            btnStart.disabled = true;
            updateCardPartial(card, 'READY');
            cleanupPoller(gameId); // Cleanup poller immediately
            await window.ATM.api.post('games/stop', { game_id: gameId }).catch(()=>{});
            btnStart.disabled = false;
        } else {
            // Start
            btnStart.disabled = true;
            
            try {
                localStorage.removeItem('atm_needs_sync_' + gameId);
                const wsRefreshBtn = document.querySelector('.btn-refresh-workspace');
                if (wsRefreshBtn) wsRefreshBtn.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
                
                updateCardPartial(card, 'TRANSLATING', 0);
                
                const res = await window.ATM.api.post('games/start', { game_id: gameId });
                
                if (res.status === 'unicode_error') {
                    updateCardPartial(card, 'READY');
                    const defaultMsg = window.ATM.i18n.t('games.auto_fix_confirm', "");
                    const msg = window.ATM.i18n ? window.ATM.i18n.t('games.unicode_error_msg', defaultMsg) : defaultMsg;
                    window.ATM.Modals.confirm(msg).then(async (agreed) => {
                        if (agreed) {
                            try {
                                const fixRes = await window.ATM.api.post('games/fix-path', { game_id: gameId });
                                if (fixRes.status === 'success') {
                                    const successMsg = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_success', '') : '';
                                    if (window.ATM.Toast) window.ATM.Toast.show(successMsg, "success");
                                    setTimeout(() => {
                                        const btn = card.querySelector('.btn-action-start');
                                        if (btn) btn.click();
                                    }, 1000);
                                } else {
                                    const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_error', '') : '';
                                    if (window.ATM.Toast) window.ATM.Toast.show(errorPrefix + (fixRes.error || 'Unknown error'), "error");
                                }
                            } catch (err) {
                                const errorPrefix = window.ATM.i18n ? window.ATM.i18n.t('games.auto_fix_error', '') : '';
                                if (window.ATM.Toast) window.ATM.Toast.show(errorPrefix + err.message, "error");
                            }
                        }
                    });
                    return;
                }

                if (res.status === 'busy' || res.status === 'error') {
                    updateCardPartial(card, 'READY');
                    if (window.ATM.Toast) {
                        const errMsg = (res.code && window.ATM.i18n ? window.ATM.i18n.t(res.code) : null)
                            || res.message
                            || res.error
                            || (window.ATM.i18n ? window.ATM.i18n.t('toast.start_failed') : 'Start failed');
                        window.ATM.Toast.show(errMsg, 'error');
                    }
                    return;
                }
                
                startPoller(gameId, card);
            } catch(e) {
                updateCardPartial(card, 'READY');
                if (window.ATM.Toast) {
                    const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.start_failed') : window.ATM.i18n.t('toast.start_failed');
                    window.ATM.Toast.show(e.message || fallback, "error");
                }
            } finally {
                btnStart.disabled = false;
            }
        }
    }

    // TASK 5: Polling Lifecycle (Stale-Response Protection, Cleanup)
    function startPoller(gameId, card) {
        if (!window.ATM.ProgressManager) return;
        
        window.ATM.ProgressManager.start(
            gameId + '_translate',
            `games/translation-status?game_id=${gameId}`,
            (status) => {
                // Ignore if card state was manually changed or if card was removed from DOM
                if (!document.contains(card) || card.dataset.state !== 'TRANSLATING') {
                    window.ATM.ProgressManager.stop(gameId + '_translate');
                    return;
                }

                if (status.done) {
                    const isRealtimeFinished = (status.code === 'translation.realtime_finished' || status.code === 'translation.ready');
                    const nextState = (status.error || isRealtimeFinished) ? 'READY' : 'COMPLETE';
                    updateCardPartial(card, nextState);
                    
                    if (window.ATM.events) {
                        window.ATM.events.publish('translation_progress', { gameId, state: nextState, percent: 100 });
                    }
                    
                    if (status.error && status.code !== 'translation.cancelled' && window.ATM.Toast) {
                        const i18n = window.ATM.i18n;
                        const errMsg = (status.code && i18n ? i18n.t(status.code) : null)
                            || status.details
                            || (i18n ? i18n.t('status.failed') : null)
                            || 'Translation Failed';
                        window.ATM.Toast.show(errMsg, 'error');
                    }
                    window.ATM.ProgressManager.stop(gameId + '_translate');
                    return;
                }
                
                const pct = (status.total > 0) ? (status.progress / status.total) * 100 : 0;
                updateCardPartial(card, 'TRANSLATING', pct);
                
                if (window.ATM.events) {
                    window.ATM.events.publish('translation_progress', { gameId, state: 'TRANSLATING', percent: pct });
                }
            }
        );
    }

    function cleanupPoller(gameId) {
        if (window.ATM.ProgressManager) {
            window.ATM.ProgressManager.stop(gameId + '_translate');
        }
    }

    async function handlePlay(gameId) {
        const card = document.getElementById(`card-${gameId}`);
        const btnStart = card ? card.querySelector('[data-action="play"]') : null;
        if (btnStart) btnStart.disabled = true;
        try {
            const initMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.initializing') : 'Initializing...';
            if (window.ATM.Toast) window.ATM.Toast.show(initMsg, false);
            await window.ATM.api.post('games/play', { game_id: gameId }); 
        } catch(e) {
            if (window.ATM.Toast) {
                const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.play_failed') : 'Play failed';
                window.ATM.Toast.show(e.message || fallback, "error");
            }
        } finally {
            if (btnStart) btnStart.disabled = false;
        }
    }

    // TASK 4: Local Mutation
    async function handleDelete(gameId, card) {
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;
        const msg = t('card.delete_confirm', "Bạn chắc chắn muốn xóa game này?");
        if (!(await window.ATM.Modals.confirm(msg))) {
            return;
        }

        const btnDel = card.querySelector('[data-action="delete"]');
        if (btnDel) btnDel.disabled = true;

        try {
            await window.ATM.api.post('games/delete', { game_id: gameId });
            
            // Clean up poller to avoid zombie requests
            cleanupPoller(gameId);
            
            // Clean up sync state in localStorage
            localStorage.removeItem('atm_needs_sync_' + gameId);
            
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
                updateCardPartial(card, 'TRANSLATING', 0);
                startPoller(data.gameId, card);
            }
        });
        window.ATM.events.subscribe('lang:changed', () => {
            loadGames();
        });
    }

    return {
        init,
        loadGames,
        load: loadGames, // Alias for app.js
        refreshLibrary,
        updateCardSyncState,
        refreshAllCardsSyncState
    };
})();

