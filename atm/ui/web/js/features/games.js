// --- atm/ui/web/js/features/games.js ---
// Architecture Rule 6: UI and DOM Manipulation ONLY. No Business Logic.
// Security Rule 8: Zero innerHTML, Zero inline handlers.

window.ATM = window.ATM || {};

window.ATM.Games = (function() {
    const containerId = 'games-container';
    let languages = {};
    let appSettings = {};
    
    // Poller Registry: 1 Game = 1 Poller
    const pollers = new Map(); // gameId -> timeoutId
    let isSelectionMode = false;
    const selectedGameIds = new Set();

    const getContainer = () => document.getElementById(containerId);

    function updateSelectionUI() {
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;
        const textDeleteSelected = document.getElementById('games-delete-selected-text');
        const btnDeleteSelected = document.getElementById('games-delete-selected-btn');
        const textSelectAll = document.getElementById('games-select-all-text');
        const container = getContainer();
        const totalCards = container ? container.querySelectorAll('.game-card').length : 0;
        const count = selectedGameIds.size;

        if (textDeleteSelected) {
            textDeleteSelected.textContent = t('games.btn_delete_selected', 'Xóa ({count})').replace('{count}', count);
        }
        if (btnDeleteSelected) {
            btnDeleteSelected.disabled = (count === 0);
        }
        if (textSelectAll) {
            if (totalCards > 0 && count === totalCards) {
                textSelectAll.textContent = t('games.btn_deselect_all', 'Bỏ chọn tất cả');
            } else {
                textSelectAll.textContent = t('games.btn_select_all', 'Chọn tất cả');
            }
        }
    }

    function enterSelectionMode() {
        isSelectionMode = true;
        selectedGameIds.clear();
        const container = getContainer();
        if (container) {
            container.classList.add('selection-mode');
        }
        const btnMode = document.getElementById('games-select-mode-btn');
        const controls = document.getElementById('games-selection-controls');
        if (btnMode) btnMode.style.display = 'none';
        if (controls) controls.style.display = 'flex';
        updateSelectionUI();
    }

    function exitSelectionMode() {
        isSelectionMode = false;
        selectedGameIds.clear();
        const container = getContainer();
        if (container) {
            container.classList.remove('selection-mode');
            container.querySelectorAll('.game-card').forEach(c => {
                c.classList.remove('is-selected');
                const cb = c.querySelector('.game-card-checkbox');
                if (cb) cb.checked = false;
            });
        }
        const btnMode = document.getElementById('games-select-mode-btn');
        const controls = document.getElementById('games-selection-controls');
        if (controls) controls.style.display = 'none';
        if (btnMode) btnMode.style.display = 'inline-flex';
    }

    function toggleCardSelection(gameId) {
        const card = document.getElementById(`card-${gameId}`);
        if (!card) return;
        const cb = card.querySelector('.game-card-checkbox');
        if (selectedGameIds.has(gameId)) {
            selectedGameIds.delete(gameId);
            card.classList.remove('is-selected');
            if (cb) cb.checked = false;
        } else {
            selectedGameIds.add(gameId);
            card.classList.add('is-selected');
            if (cb) cb.checked = true;
        }
        updateSelectionUI();
    }

    function toggleSelectAll() {
        const container = getContainer();
        if (!container) return;
        const cards = container.querySelectorAll('.game-card');
        if (cards.length === 0) return;

        const allSelected = (selectedGameIds.size === cards.length);
        if (allSelected) {
            selectedGameIds.clear();
            cards.forEach(c => {
                c.classList.remove('is-selected');
                const cb = c.querySelector('.game-card-checkbox');
                if (cb) cb.checked = false;
            });
        } else {
            cards.forEach(c => {
                const id = c.dataset.gameId;
                if (id) {
                    selectedGameIds.add(id);
                    c.classList.add('is-selected');
                    const cb = c.querySelector('.game-card-checkbox');
                    if (cb) cb.checked = true;
                }
            });
        }
        updateSelectionUI();
    }

    async function handleBatchDelete() {
        if (selectedGameIds.size === 0) return;
        const count = selectedGameIds.size;
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;
        const ids = Array.from(selectedGameIds);

        const btnDeleteSelected = document.getElementById('games-delete-selected-btn');
        if (btnDeleteSelected) btnDeleteSelected.disabled = true;

        let totalSizeMb = 0;
        try {
            await Promise.all(ids.map(async (id) => {
                try {
                    const res = await window.ATM.api.get(`games/delete-info?game_id=${id}`);
                    if (res && res.status === 'success' && res.size_mb) {
                        totalSizeMb += res.size_mb;
                    }
                } catch (e) {
                    console.warn(`Failed to get delete info for ${id}`, e);
                }
            }));
        } catch (e) {
            console.error("Error calculating batch delete size", e);
        }

        totalSizeMb = Math.round(totalSizeMb * 100) / 100;

        const msgTemplate = t('games.delete_multiple_confirm', 'Bạn có chắc chắn muốn xóa {count} game đã chọn? (Sẽ hoàn nguyên file game về nguyên bản)');
        const msg = msgTemplate.replace('{count}', count);

        const cbLabelTemplate = t('card.delete_purge_data', 'Xóa vĩnh viễn dữ liệu dịch (Giải phóng ~{size}MB Database). Nếu không tích, dữ liệu sẽ được giữ lại để phục hồi sau này.');
        const cbLabel = cbLabelTemplate.replace('{size}', totalSizeMb);

        const result = await window.ATM.Modals.confirm(msg, { checkboxLabel: cbLabel });
        if (!result || !result.agreed) {
            if (btnDeleteSelected) btnDeleteSelected.disabled = (selectedGameIds.size === 0);
            return;
        }

        let successCount = 0;
        for (const gameId of ids) {
            try {
                await window.ATM.api.post('games/delete', { game_id: gameId, purge_data: result.checked });
                cleanupPoller(gameId);
                localStorage.removeItem('atm_needs_sync_' + gameId);
                const card = document.getElementById(`card-${gameId}`);
                if (card) card.remove();
                successCount++;
            } catch (err) {
                console.error(`Failed to delete game ${gameId}`, err);
            }
        }

        exitSelectionMode();

        const successMsg = t('games.delete_multiple_success', 'Đã xóa thành công {count} game').replace('{count}', successCount);
        if (window.ATM.Toast) {
            window.ATM.Toast.show(successMsg, 'success');
        }

        const container = getContainer();
        if (container && container.querySelectorAll('.game-card').length === 0) {
            renderEmptyState(container);
            const btnMode = document.getElementById('games-select-mode-btn');
            if (btnMode) btnMode.style.display = 'none';
        }
    }

    function isEngineConfigured(engine) {
        if (!engine || engine === 'google') return true;
        if (engine === 'custom_llm') {
            return Boolean(appSettings.custom_llm_configured || (appSettings.custom_llm_model && appSettings.custom_llm_base_url));
        }
        return Boolean(appSettings[`${engine}_api_key_configured`]);
    }

    function getEngineOptions() {
        const readyText = window.ATM.i18n ? window.ATM.i18n.t('games.engine_ready', 'Sẵn sàng') : 'Sẵn sàng';
        const noKeyText = window.ATM.i18n ? window.ATM.i18n.t('games.engine_no_key', 'Chưa có Key') : 'Chưa có Key';

        return [
            { value: 'google', text: `Google Translate [✓ ${readyText}]` },
            { value: 'gemini', text: `Google Gemini [${isEngineConfigured('gemini') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'deepseek', text: `DeepSeek (V3/R1) [${isEngineConfigured('deepseek') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'openai', text: `OpenAI (ChatGPT) [${isEngineConfigured('openai') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'claude', text: `Anthropic Claude [${isEngineConfigured('claude') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'kimi', text: `Kimi (Moonshot) [${isEngineConfigured('kimi') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'custom_llm', text: `Custom / Local LLM [${isEngineConfigured('custom_llm') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` },
            { value: 'deepl', text: `DeepL API [${isEngineConfigured('deepl') ? '✓ ' + readyText : '⚠️ ' + noKeyText}]` }
        ];
    }

    function updateCardEngineWarning(card) {
        if (!card) return;
        const engineSel = card.querySelector('.engine-select');
        if (!engineSel) return;
        const engine = engineSel.value;
        const isConfigured = isEngineConfigured(engine);
        const btnStart = card.querySelector('.btn-action-start');

        let warningEl = card.querySelector('.engine-key-warning');

        if (!isConfigured) {
            engineSel.classList.add('needs-key');
            if (btnStart && card.dataset.state !== 'TRANSLATING') {
                btnStart.classList.add('needs-key');
                btnStart.title = window.ATM.i18n ? window.ATM.i18n.t('games.engine_warning_tooltip', 'Cần cấu hình API Key trong Cài đặt để sử dụng') : 'Cần cấu hình API Key trong Cài đặt để sử dụng';
            }
            if (!warningEl) {
                warningEl = document.createElement('div');
                warningEl.className = 'engine-key-warning';
                warningEl.textContent = window.ATM.i18n ? `⚠️ ${window.ATM.i18n.t('games.engine_warning_tooltip', 'Cần cấu hình API Key')}` : '⚠️ Cần cấu hình API Key';
                const parent = engineSel.parentNode;
                if (parent) parent.appendChild(warningEl);
            }
        } else {
            engineSel.classList.remove('needs-key');
            if (btnStart) {
                btnStart.classList.remove('needs-key');
                btnStart.title = '';
            }
            if (warningEl) {
                warningEl.remove();
            }
        }
    }

    function refreshAllEngineSelects() {
        const container = getContainer();
        if (!container) return;
        const cards = container.querySelectorAll('.game-card');
        const opts = getEngineOptions();

        cards.forEach(card => {
            const engineSel = card.querySelector('.engine-select');
            if (!engineSel) return;
            const currentVal = engineSel.value;
            buildOptions(engineSel, opts, currentVal);
            updateCardEngineWarning(card);
        });
    }

    // Initializer
    async function init() {
        try {
            const [langs, s] = await Promise.all([
                window.ATM.api.get('languages'),
                window.ATM.api.get('settings')
            ]);
            languages = langs || {};
            appSettings = s || {};
        } catch (err) {
            console.error("Failed to init settings or languages:", err);
        }
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
        if (window.ATM.events) {
            window.ATM.events.subscribe('settings:updated', (newSettings) => {
                appSettings = newSettings || {};
                refreshAllEngineSelects();
            });
        }
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
                        const i18n = window.ATM.i18n;
                        const code = res.code;
                        const msg = (i18n && code && i18n.t(code)) ? i18n.t(code) : (res.error || (i18n ? i18n.t('toast.add_game_error') : 'Add game error'));
                        if (window.ATM.Toast) window.ATM.Toast.show(msg, "error");
                    }
                } catch(e) {
                    console.error("Failed to add game:", e);
                    const i18n = window.ATM.i18n;
                    const code = e.code || (e.data && e.data.code);
                    const msg = (i18n && code && i18n.t(code)) ? i18n.t(code) : (e.message || (i18n ? i18n.t('toast.add_game_error') : 'Add game error'));
                    if (window.ATM.Toast) window.ATM.Toast.show(msg, "error");
                } finally {
                    btnAdd.disabled = false;
                }
            });
        }

        const container = getContainer();
        const btnSelectMode = document.getElementById('games-select-mode-btn');
        const btnSelectAll = document.getElementById('games-select-all-btn');
        const btnDeleteSelected = document.getElementById('games-delete-selected-btn');
        const btnCancelSelect = document.getElementById('games-cancel-select-btn');

        if (btnSelectMode) btnSelectMode.addEventListener('click', enterSelectionMode);
        if (btnSelectAll) btnSelectAll.addEventListener('click', toggleSelectAll);
        if (btnDeleteSelected) btnDeleteSelected.addEventListener('click', handleBatchDelete);
        if (btnCancelSelect) btnCancelSelect.addEventListener('click', exitSelectionMode);

        if (!container) return;

        container.addEventListener('click', async (e) => {
            if (isSelectionMode) {
                const card = e.target.closest('.game-card');
                if (card && card.dataset.gameId) {
                    toggleCardSelection(card.dataset.gameId);
                }
                return;
            }

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
                
                // Block changing engine while translating
                if (card.dataset.state === 'TRANSLATING') {
                    if (window.ATM.Toast) {
                        const msg = window.ATM.i18n ? window.ATM.i18n.t('games.cannot_change_engine') : 'Không thể thay đổi bộ dịch khi đang dịch!';
                        window.ATM.Toast.show(msg, 'warning');
                    }
                    return;
                }

                const gameId = card.dataset.gameId;
                const engine = card.querySelector('.engine-select').value;
                const source = card.querySelector('.source-select').value;
                const target = card.querySelector('.target-select').value;

                updateCardEngineWarning(card);
                
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
        card.dataset.engine = game.engine || 'Unknown';
        card.dataset.lines = game.runtime_lines || 0;
        
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
            badgeEl.textContent = game.engine === 'Bakin' ? 'Bakin (BETA)' : (game.engine || 'Unknown');
            badgeEl.dataset.engine = game.engine || 'Unknown';
        }
        
        // Avatar
        const avatar = card.querySelector('.game-avatar');
        if (avatar) {
            avatar.textContent = gameName.charAt(0).toUpperCase();
        }

        // Build Selectors
        const engineSel = card.querySelector('.engine-select');
        buildOptions(engineSel, getEngineOptions(), game.translator);
        updateCardEngineWarning(card);

        const srcSel = card.querySelector('.source-select');
        buildOptions(srcSel, langArr, game.input_lang, false);

        const tgtSel = card.querySelector('.target-select');
        buildOptions(tgtSel, langArr, game.output_lang, true);

        const btnPlay = card.querySelector('.btn-play');
        if (btnPlay) {
            if (card.dataset.state === 'TRANSLATING') {
                btnPlay.disabled = true;
                btnPlay.setAttribute('data-i18n-title', 'card.play_disabled_translating');
                btnPlay.title = window.ATM.i18n ? window.ATM.i18n.t('card.play_disabled_translating') : 'Game is translating';
            } else {
                btnPlay.disabled = false;
                btnPlay.setAttribute('data-i18n-title', 'card.play_tooltip');
                btnPlay.title = window.ATM.i18n ? window.ATM.i18n.t('card.play_tooltip') : 'Play Game';
            }
        }

        const checkbox = card.querySelector('.game-card-checkbox');
        if (checkbox) {
            checkbox.checked = selectedGameIds.has(game.id);
            if (selectedGameIds.has(game.id)) {
                card.classList.add('is-selected');
            }
        }

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
            const btnMode = document.getElementById('games-select-mode-btn');
            if (btnMode && !isSelectionMode) {
                btnMode.style.display = 'inline-flex';
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
        if (isSelectionMode) {
            exitSelectionMode();
        }

        try {
            const data = await window.ATM.api.get('games');
            const games = data.games || [];
            
            const btnMode = document.getElementById('games-select-mode-btn');
            if (btnMode) {
                btnMode.style.display = games.length > 0 ? 'inline-flex' : 'none';
            }

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
                    card.dataset.lines = game.runtime_lines || 0;
                    card.dataset.engine = game.engine || 'Unknown';
                    const pct = game.runtime_total ? Math.round((game.runtime_progress / game.runtime_total) * 100) : 0;
                    const initialStatus = (game.runtime_state === 'TRANSLATING' && (game.engine || '').includes('Unity')) ? {
                        code: 'translation.realtime_running',
                        translated_lines: game.runtime_lines || 0
                    } : null;
                    updateCardPartial(card, card.dataset.state, pct, initialStatus);
                    
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
    function updateCardPartial(card, state, percent = 0, statusObj = null) {
        card.dataset.state = state;
        
        const btnStart = card.querySelector('.btn-action-start');
        const progContainer = card.querySelector('.progress-container');
        const progBarFill = card.querySelector('.progress-bar-fill');
        const progPercent = card.querySelector('.progress-percent');
        const progStatus = card.querySelector('.progress-status');
        const statusBadge = card.querySelector('.status-badge');

        if (!btnStart) return;

        const t = (k, fb) => (window.ATM.i18n ? window.ATM.i18n.t(k, fb) : fb);

        // Independent Play Button state management
        const btnPlay = card.querySelector('.btn-play');
        if (btnPlay) {
            if (state === 'TRANSLATING') {
                btnPlay.disabled = true;
                btnPlay.setAttribute('data-i18n-title', 'card.play_disabled_translating');
                btnPlay.title = t('card.play_disabled_translating', 'Game đang dịch, không thể khởi chạy');
            } else {
                btnPlay.disabled = false;
                btnPlay.setAttribute('data-i18n-title', 'card.play_tooltip');
                btnPlay.title = t('card.play_tooltip', 'Chơi Game');
            }
            
            if (state === 'COMPLETE') {
                btnPlay.className = 'btn-success flex-1 btn-play';
                btnPlay.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><line x1="6" y1="12" x2="10" y2="12"></line><line x1="8" y1="10" x2="8" y2="14"></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line x1="18" y1="11" x2="18.01" y2="11"></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg><span data-i18n="card.play_now"></span>';
                const span = btnPlay.querySelector('span');
                if (span) span.textContent = t('card.play_now', 'Chơi Game Ngay');
            } else {
                btnPlay.className = 'btn-icon btn-play';
                btnPlay.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="12" x2="10" y2="12"></line><line x1="8" y1="10" x2="8" y2="14"></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line x1="18" y1="11" x2="18.01" y2="11"></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg>';
            }
        }

        // Toggle input select availability based on state
        const selects = card.querySelectorAll('.engine-select, .source-select, .target-select');
        if (state === 'TRANSLATING') {
            selects.forEach(s => s.disabled = true);
        } else {
            selects.forEach(s => s.disabled = false);
            updateCardEngineWarning(card);
        }

        // Independent Delete Button state management
        const btnDelete = card.querySelector('.btn-delete[data-action="delete"]');
        if (btnDelete) {
            if (state === 'TRANSLATING') {
                btnDelete.disabled = true;
                btnDelete.style.opacity = '0.5';
                btnDelete.style.cursor = 'not-allowed';
                btnDelete.title = t('card.delete_disabled_translating', 'Không thể xóa khi đang dịch');
            } else {
                btnDelete.disabled = false;
                btnDelete.style.opacity = '';
                btnDelete.style.cursor = '';
                btnDelete.title = t('card.delete_tooltip', 'Xóa game');
            }
        }

        if (state === 'READY') {
            btnStart.setAttribute('data-i18n', 'card.start');
            btnStart.textContent = t('card.start', 'Bắt đầu dịch');
            btnStart.className = "btn-start flex-1 btn-action-start";
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'none';
            progContainer.classList.add('hidden');
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
            progContainer.classList.remove('hidden');
            
            const isUnity = (card.dataset.engine || '').includes('Unity');
            if (isUnity || (statusObj && statusObj.code === 'translation.realtime_running')) {
                if (progBarFill) {
                    progBarFill.style.width = '100%';
                    progBarFill.classList.add('progress-bar-animated');
                }
                const linesCount = (statusObj && statusObj.translated_lines !== undefined)
                    ? statusObj.translated_lines
                    : (card.dataset.lines ? parseInt(card.dataset.lines, 10) : 0);
                if (progPercent) {
                    progPercent.textContent = `${linesCount} ${t('common.lines', 'câu')}`;
                }
                if (progStatus) {
                    progStatus.textContent = t('translation.realtime_running', 'Đang dịch trong game (Real-time)...');
                }
            } else {
                if (progBarFill) {
                    progBarFill.classList.remove('progress-bar-animated');
                    progBarFill.style.width = `${Math.min(100, Math.max(0, percent))}%`;
                }
                if (progPercent) progPercent.textContent = `${Math.round(percent)}%`;
                if (progStatus) progStatus.textContent = t('card.translating', 'Đang dịch...');
            }
            
            if (statusBadge) {
                statusBadge.textContent = t('status.running', 'Đang dịch...');
                statusBadge.style.backgroundColor = "rgba(59, 130, 246, 0.1)"; // accent tinted
                statusBadge.style.color = "var(--accent)";
            }
        }
        else if (state === 'COMPLETE') {
            btnStart.removeAttribute('data-i18n');
            btnStart.className = "btn-icon btn-warning btn-action-start";
            btnStart.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>`;
            btnStart.setAttribute('data-i18n-title', 'card.retranslate');
            btnStart.title = t('card.retranslate', 'Dịch Lại');
            btnStart.style.color = "";
            btnStart.style.backgroundColor = "";
            btnStart.style.border = "";
            btnStart.dataset.action = "start";
            progContainer.style.display = 'none';
            progContainer.classList.add('hidden');
            
            if (statusBadge) {
                statusBadge.textContent = t('status.completed', 'Hoàn thành');
                statusBadge.style.backgroundColor = "rgba(16, 185, 129, 0.1)"; // success tinted
                statusBadge.style.color = "var(--success)";
            }
            
            const needsSync = localStorage.getItem('atm_needs_sync_' + card.dataset.gameId) === 'true';
            if (needsSync) {
                btnStart.className = "btn-delete heartbeat-neon-red flex-1 btn-action-start";
                btnStart.innerHTML = t('games.btn_sync', 'Đồng bộ & Dịch');
                btnStart.removeAttribute('data-i18n-title');
                btnStart.removeAttribute('title');
                btnStart.dataset.action = "start";
                // Restore Play button to icon if Sync is needed to avoid width overflow
                if (btnPlay) {
                    btnPlay.className = 'btn-icon btn-play';
                    btnPlay.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="12" x2="10" y2="12"></line><line x1="8" y1="10" x2="8" y2="14"></line><line x1="15" y1="13" x2="15.01" y2="13"></line><line x1="18" y1="11" x2="18.01" y2="11"></line><rect x="2" y="6" width="20" height="12" rx="2"></rect></svg>`;
                }
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
            progContainer.classList.remove('hidden');
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
            progContainer.classList.add('hidden');
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
            // Check engine configuration before starting
            const engineSel = card.querySelector('.engine-select');
            const selectedEngine = engineSel ? engineSel.value : 'google';
            if (!isEngineConfigured(selectedEngine)) {
                if (window.ATM.Toast) {
                    const engineName = selectedEngine.toUpperCase();
                    const msg = window.ATM.i18n ? window.ATM.i18n.t('toast.no_ai_key', { engine: engineName }) : `Vui lòng cấu hình API Key cho ${engineName} trước khi bắt đầu dịch!`;
                    window.ATM.Toast.show(msg, 'error');
                }
                updateCardEngineWarning(card);
                return;
            }

            // Start
            btnStart.disabled = true;
            
            try {
                localStorage.removeItem('atm_needs_sync_' + gameId);
                const wsRefreshBtn = document.querySelector('.btn-refresh-workspace');
                if (wsRefreshBtn) wsRefreshBtn.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
                
                const isUnity = (card.dataset.engine || '').includes('Unity');
                const initialStatus = isUnity ? {
                    code: 'translation.realtime_running',
                    translated_lines: card.dataset.lines ? parseInt(card.dataset.lines, 10) : 0
                } : null;
                updateCardPartial(card, 'TRANSLATING', 0, initialStatus);
                
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
                        const errMsg = (res.code && window.ATM.i18n ? window.ATM.i18n.t(res.code, res.params) : null)
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
                        const errMsg = (status.code && i18n ? i18n.t(status.code, status.params || {}) : null)
                            || status.details
                            || (i18n ? i18n.t('status.failed') : null)
                            || 'Translation Failed';
                        window.ATM.Toast.show(errMsg, 'error');
                    }
                    window.ATM.ProgressManager.stop(gameId + '_translate');
                    return;
                }
                
                if (status.translated_lines !== undefined) {
                    card.dataset.lines = status.translated_lines;
                }
                const pct = (status.total > 0) ? (status.progress / status.total) * 100 : 0;
                updateCardPartial(card, 'TRANSLATING', pct, status);
                
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
        if (card && card.dataset.state === 'TRANSLATING') {
            const warnMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.game_translating') : 'Game is currently translating!';
            if (window.ATM.Toast) window.ATM.Toast.show(warnMsg, "warning");
            return;
        }
        const btnPlay = card ? card.querySelector('[data-action="play"]') : null;
        if (btnPlay) btnPlay.disabled = true;
        try {
            const initMsg = window.ATM.i18n ? window.ATM.i18n.t('toast.initializing') : 'Initializing...';
            if (window.ATM.Toast) window.ATM.Toast.show(initMsg, "info");
            const res = await window.ATM.api.post('games/play', { game_id: gameId });
            if (res && res.status === 'error') {
                const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.play_failed') : 'Play failed';
                const code = res.code;
                const msg = (window.ATM.i18n && code && window.ATM.i18n.t(code)) ? window.ATM.i18n.t(code) : (res.error || fallback);
                if (window.ATM.Toast) window.ATM.Toast.show(msg, "error");
            }
        } catch(e) {
            if (window.ATM.Toast) {
                const fallback = window.ATM.i18n ? window.ATM.i18n.t('toast.play_failed') : 'Play failed';
                const code = e.code || (e.data && e.data.code);
                const msg = (window.ATM.i18n && code && window.ATM.i18n.t(code)) ? window.ATM.i18n.t(code) : (e.error || e.message || fallback);
                window.ATM.Toast.show(msg, "error");
            }
        } finally {
            if (btnPlay && (!card || card.dataset.state !== 'TRANSLATING')) {
                btnPlay.disabled = false;
            }
        }
    }

    // TASK 4: Local Mutation
    async function handleDelete(gameId, card) {
        const t = (key, fallback) => window.ATM.i18n ? window.ATM.i18n.t(key, fallback) : fallback;
        const btnDel = card.querySelector('[data-action="delete"]');
        if (btnDel) btnDel.disabled = true;

        let sizeMb = 0;
        try {
            const sizeRes = await window.ATM.api.get(`games/delete-info?game_id=${gameId}`);
            if (sizeRes.status === 'success' && sizeRes.size_mb) {
                sizeMb = sizeRes.size_mb;
            }
        } catch (e) {
            console.warn("Failed to get game delete info", e);
        }

        const msg = t('card.delete_confirm', "Bạn có chắc chắn muốn xóa game này? (Sẽ hoàn nguyên file game về nguyên bản)");
        const cbLabelText = t('card.delete_purge_data', "Xóa vĩnh viễn dữ liệu dịch (Giải phóng ~{size}MB Database). Nếu không tích, dữ liệu sẽ được giữ lại để phục hồi sau này.");
        const cbLabel = cbLabelText.replace('{size}', sizeMb);

        const result = await window.ATM.Modals.confirm(msg, { checkboxLabel: cbLabel });
        if (!result || !result.agreed) {
            if (btnDel) btnDel.disabled = false;
            return;
        }

        try {
            await window.ATM.api.post('games/delete', { game_id: gameId, purge_data: result.checked });
            
            // Clean up poller to avoid zombie requests
            cleanupPoller(gameId);
            
            // Clean up sync state in localStorage
            localStorage.removeItem('atm_needs_sync_' + gameId);
            
            // Local mutation: Remove from DOM
            card.remove();
            
            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.delete_success'));
            
            // Check if empty
            const container = getContainer();
            if (container && container.querySelectorAll('.game-card').length === 0) {
                renderEmptyState(container);
                const btnMode = document.getElementById('games-select-mode-btn');
                if (btnMode) btnMode.style.display = 'none';
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
            refreshAllEngineSelects();
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

