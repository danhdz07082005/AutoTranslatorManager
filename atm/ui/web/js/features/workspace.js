window.ATM = window.ATM || {};
window.ATM.features = window.ATM.features || {};

/**
 * ATM.Workspace
 * Architecture Rule 6: Manage Lifecycle (open, mount, leave, destroy)
 */
(function() {
    let currentGame = null;

    let currentFetchCtrl = null;

    function open(gameId) {
        if (window.ATM.navigation) {
            window.ATM.navigation.showWorkspace(gameId);
        }
        
        if (currentFetchCtrl) currentFetchCtrl.abort();
        currentFetchCtrl = new AbortController();
        
        // Fetch game details to show in header
        window.ATM.api.get(`games`, { signal: currentFetchCtrl.signal })
            .then(data => {
                if (!document.getElementById('workspace-container')) return; // View changed
                
                const game = data.games.find(g => g.id === gameId);
                if (game) {
                    currentGame = game;
                    const titleEl = document.getElementById('workspace-title');
                    const subtitleEl = document.getElementById('workspace-subtitle');
                    if (titleEl) titleEl.textContent = game.game_name || 'Unknown Game';
                    if (subtitleEl) {
                        subtitleEl.innerHTML = `Engine: <span class="engine-badge" data-engine="${game.engine || 'Unknown'}">${game.engine || 'Unknown'}</span> &nbsp;|&nbsp; Translator: <span class="engine-badge translator-badge">${game.translator || 'Google'}</span>`;
                    }
                    
                    mount(game);
                } else {
                    console.error("Game not found in library");
                    leave();
                }
            })
            .catch(err => {
                console.error("Failed to fetch game details:", err);
            });
    }

    function mount(game) {
        const container = document.getElementById('workspace-container');
        if (!container) return;
        
        const template = document.getElementById('workspace-shell-template');
        if (!template) {
            console.error("Missing workspace-shell-template");
            return;
        }
        
        const clone = template.content.cloneNode(true);
                const dockStatusText = clone.querySelector('.workspace-status-text');
        if (dockStatusText) dockStatusText.id = `workspace-status-text-${game.id}`;

        const dockPercentText = clone.querySelector('.workspace-percent-text');
        if (dockPercentText) dockPercentText.id = `workspace-percent-text-${game.id}`;
        
        const dockProgressBar = clone.querySelector('.workspace-progress-bar');
        if (dockProgressBar) dockProgressBar.id = `workspace-progress-bar-${game.id}`;

        const btnRefresh = clone.querySelector('.btn-refresh-workspace');
        if (btnRefresh) {
            if (localStorage.getItem('atm_needs_sync_' + game.id) === 'true') {
                btnRefresh.classList.add('btn-needs-sync');
            }
            btnRefresh.addEventListener('click', () => {
                if (!currentGame) return;
                const i18n = window.ATM.i18n;
                const confirmMsg = i18n ? i18n.t('confirm.sync_translation') : 'Sync translation data?';
                
                if (window.ATM.Modals && window.ATM.Modals.confirm) {
                    window.ATM.Modals.confirm(confirmMsg).then(agreed => {
                        if (!agreed) return;
                        doSync();
                    });
                } else {
                    if (!confirm(confirmMsg)) return;
                    doSync();
                }

                function doSync() {
                    if (!currentGame) return;
                    btnRefresh.classList.remove('btn-needs-sync');
                    const gameId = currentGame.id;
                    localStorage.removeItem('atm_needs_sync_' + gameId);
                    const statusText = document.getElementById(`workspace-status-text-${gameId}`);
                    const percentText = document.getElementById(`workspace-percent-text-${gameId}`);
                    const progressBar = document.getElementById(`workspace-progress-bar-${gameId}`);
                    
                    if (statusText && percentText) {
                        statusText.textContent = i18n ? i18n.t('workspace.refreshing') : 'Syncing...';
                        statusText.style.color = '#8b5cf6';
                        percentText.style.color = '#8b5cf6';
                    }
                    if (progressBar) {
                        progressBar.style.backgroundColor = '#8b5cf6';
                    }
                    
                    window.ATM.api.post('games/sync', { game_id: gameId })
                        .then((res) => {
                            if (res.is_running) {
                                setTimeout(() => {
                                    if (window.ATM.events) {
                                        window.ATM.events.publish('force_poller_restart', { gameId: gameId });
                                    }
                                }, 1000);
                            }
                            if (window.ATM.Toast) {
                                const now = new Date();
                                const timeStr = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0') + ':' + now.getSeconds().toString().padStart(2, '0');
                                let msg = i18n ? i18n.t('workspace.sync_success') : '[OK] Synced at {time}';
                                if (msg) msg = msg.replace('{time}', timeStr);
                                window.ATM.Toast.show(msg, 'success');
                            }
                        })
                        .catch(e => {
                            if (window.ATM.Toast) {
                                let fallback = i18n ? i18n.t('error.sync_failed') : 'Sync Error';
                                window.ATM.Toast.show(e.error || fallback, 'error');
                            }
                            if (window.ATM.polling) window.ATM.polling.pollTranslation(currentGame.id);
                        });
                }
            });
        }

        const tabEditor = clone.querySelector('.tab-editor');
        const tabGlossary = clone.querySelector('.tab-glossary');
        const tabTm = clone.querySelector('.tab-tm');
        const tabAudit = clone.querySelector('.tab-audit');
        const tabExtract = clone.querySelector('.tab-extract');
        
        if (tabGlossary) {
            tabGlossary.addEventListener('click', () => {
                if(window.ATM.Glossary) window.ATM.Glossary.open(game.id);
            });
        }
        if (tabTm) {
            tabTm.addEventListener('click', () => {
                if(window.ATM.Modals) window.ATM.Modals.open('translation-memory-modal');
            });
        }
        
        if (['Bakin'].includes(game.engine)) {
            if (tabAudit) {
                tabAudit.style.display = 'block';
                tabAudit.addEventListener('click', () => window.ATM.Workspace.auditCoverage(game.id, game.engine));
            }
            if (tabExtract) {
                tabExtract.style.display = 'block';
                tabExtract.addEventListener('click', () => window.ATM.Workspace.runExtractJob(game.id));
            }
        }
        
        // Cập nhật id động cho các element theo game.id (nếu cần cho poller truy xuất)
        const progressContainer = clone.querySelector('.job-progress-container');
        if (progressContainer) progressContainer.id = `job-progress-container-${game.id}`;
        
        const progressText = clone.querySelector('.job-progress-text');
        if (progressText) progressText.id = `job-progress-text-${game.id}`;
        
        const progressBar = clone.querySelector('.job-progress-bar');
        if (progressBar) progressBar.id = `job-progress-bar-${game.id}`;
        
        container.replaceChildren(clone);
        if (window.ATM.i18n && window.ATM.i18n.updateDOM) window.ATM.i18n.updateDOM();
        
        const card = document.getElementById(`card-${game.id}`);
        const initPct = (card && card.dataset.percent) ? parseFloat(card.dataset.percent) : 0;
        const initState = (card && card.dataset.state) ? card.dataset.state : (game.runtime_state || 'READY');
        updateProgress(game.id, initState, initPct);
        
        startEditor(game.id);
        
    }

    
    function updateProgress(gameId, state, percent) {
        const statusText = document.getElementById(`workspace-status-text-${gameId}`);
        const percentText = document.getElementById(`workspace-percent-text-${gameId}`);
        const progressBar = document.getElementById(`workspace-progress-bar-${gameId}`);
        const i18n = window.ATM.i18n;
        
        let displayPercent = percent;
        if (state === 'COMPLETE') {
            displayPercent = 100;
        }
        
        if (statusText && percentText) {
            percentText.textContent = `${displayPercent.toFixed(1)}%`;
            if (state === 'TRANSLATING') {
                statusText.setAttribute('data-i18n', 'status.running');
                statusText.textContent = (i18n ? i18n.t('status.running') : 'Translating...');
                statusText.style.color = 'var(--accent)';
                percentText.style.color = 'var(--accent)';
            } else if (state === 'COMPLETE') {
                statusText.setAttribute('data-i18n', 'status.completed');
                statusText.textContent = (i18n ? i18n.t('status.completed') : 'Completed');
                statusText.style.color = 'var(--success)';
                percentText.style.color = 'var(--success)';
            } else if (state === 'INTERRUPTED' || state === 'PAUSED') {
                statusText.setAttribute('data-i18n', 'status.interrupted');
                statusText.textContent = (i18n ? i18n.t('status.interrupted') : 'Interrupted');
                statusText.style.color = 'var(--warning)';
                percentText.style.color = 'var(--warning)';
            } else {
                statusText.setAttribute('data-i18n', 'workspace.status_ready');
                statusText.textContent = (i18n ? i18n.t('workspace.status_ready') : 'Ready');
                statusText.style.color = 'var(--text-secondary)';
                percentText.style.color = 'var(--text-secondary)';
            }
        }
        if (progressBar) {
            progressBar.style.width = `${displayPercent}%`;
            progressBar.style.backgroundColor = state === 'TRANSLATING' ? 'var(--accent)' : (state === 'COMPLETE' ? 'var(--success)' : 'var(--text-muted)');
        }
    }

    function startEditor(gameId) {
        const mountPoint = document.getElementById('editor-workspace-mount');
        const template = document.getElementById('workspace-editor-template');
        
        if (mountPoint && template) {
            mountPoint.replaceChildren(template.content.cloneNode(true));
            if (window.ATM.i18n && typeof window.ATM.i18n.updateDOM === 'function') {
                window.ATM.i18n.updateDOM();
            }
            if (window.ATM.Editor) {
                window.ATM.Editor.open(gameId);
            }
        }
    }

    function cleanup() {
        if (currentGame) {
            if (window.ATM.ProgressManager) {
                window.ATM.ProgressManager.stop(currentGame.id + '_extract');
            }
            if (window.ATM.Editor) {
                window.ATM.Editor.close();
            }
        }
        currentGame = null;
        const container = document.getElementById('workspace-container');
        if (container) container.replaceChildren(); // Clean up memory
    }

    function leave() {
        cleanup();
        if (window.ATM.Editor) window.ATM.Editor.close();
        if (window.ATM.ProgressManager) window.ATM.ProgressManager.stop('extract_job');
        if (window.ATM.navigation) {
            window.ATM.navigation.showLibrary();
        }
    }

    // Init listeners (script is deferred, so DOM is ready)
    const backBtn = document.getElementById('workspace-back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', leave);
    }
    
    // Global translation progress listener
    if (window.ATM.events && !window.ATM.Workspace?._progSubscribed) {
        window.ATM.events.subscribe('translation_progress', (data) => {
            if (currentGame && String(data.gameId) === String(currentGame.id)) {
                updateProgress(data.gameId, data.state, data.percent);
            }
        });
        window.ATM.events.subscribe('glossary:changed', (payload) => {
            if (payload && payload.gameId) {
                localStorage.setItem('atm_needs_sync_' + payload.gameId, 'true');
            }
            if (payload && payload.gameId && currentGame && payload.gameId !== currentGame.id) return;
            const btn = document.querySelector('.btn-refresh-workspace');
            if (btn) btn.classList.add('btn-needs-sync');
        });
        // We defer attaching the flag to window.ATM.Workspace below
    }

    async function auditCoverage(gameId, engine) {
        try {
            const res = await window.ATM.api.get(`engines/coverage?game_id=${gameId}`);
            const data = res;
            window.ATM.Modals.info(`${engine} Coverage Report`, 
                `Total: ${data.total}\nTranslated: ${data.translated}\nUntranslated: ${data.untranslated}\nCoverage: ${data.coverage_percent}%`);
        } catch (e) {
            window.ATM.Toast.show(`Failed to audit ${engine} coverage.`, "error");
        }
    }

    async function runExtractJob(gameId) {
        try {
            const res = await window.ATM.api.post('jobs/extract', { game_id: gameId });
            if (res.error) {
                window.ATM.Toast.show(res.error, "error");
                return;
            }
            if (res.status === 'already_running') {
                window.ATM.Toast.show('Job is already running!', 'info');
            } else {
                window.ATM.Toast.show('Extract job started.', 'success');
            }
            
            const jobId = res.job_id;
            if (!jobId) return;
            
            const container = document.getElementById(`job-progress-container-${gameId}`);
            const textEl = document.getElementById(`job-progress-text-${gameId}`);
            const barEl = document.getElementById(`job-progress-bar-${gameId}`);
            
            if (container) container.style.display = 'flex';
            
            if (window.ATM.ProgressManager) {
                window.ATM.ProgressManager.start(
                    gameId + '_extract',
                    `jobs/${jobId}`,
                    (status) => {
                        if (status.status === 'running' || status.status === 'queued') {
                            if (textEl) {
                                textEl.textContent = status.message || (status.progress && status.progress.percent !== undefined ? `${status.progress.percent}%` : status.status);
                            }
                            if (barEl && status.progress && status.progress.percent !== undefined) {
                                barEl.style.width = `${status.progress.percent}%`;
                            }
                        } else if (status.status === 'completed') {
                            if (textEl) textEl.textContent = 'Completed';
                            if (barEl) barEl.style.width = '100%';
                            setTimeout(() => { if (container) container.style.display = 'none'; }, 3000);
                            window.ATM.Toast.show('Extract job completed!', 'success');
                        } else if (status.status === 'failed' || status.status === 'cancelled') {
                            if (textEl) textEl.textContent = status.status;
                            setTimeout(() => { if (container) container.style.display = 'none'; }, 3000);
                            window.ATM.Toast.show(`Extract job ${status.status}`, 'error');
                        }
                    }
                );
            }
        } catch (e) {
            alert('Failed to start extract job.');
        }
    }

    window.ATM.Workspace = {
        _progSubscribed: true,
        open,
        auditCoverage,
        runExtractJob,
        leave,
        mount,
        startEditor
    };
})();

