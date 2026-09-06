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
                        subtitleEl.replaceChildren();
                        subtitleEl.appendChild(document.createTextNode('Engine: '));
                        const engineSpan = document.createElement('span');
                        engineSpan.className = 'engine-badge';
                        engineSpan.dataset.engine = game.engine || 'Unknown';
                        engineSpan.textContent = game.engine || 'Unknown';
                        subtitleEl.appendChild(engineSpan);
                        subtitleEl.appendChild(document.createTextNode(' \u00a0|\u00a0 Translator: '));
                        const transSpan = document.createElement('span');
                        transSpan.className = 'engine-badge translator-badge';
                        transSpan.textContent = game.translator || 'Google';
                        subtitleEl.appendChild(transSpan);
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
            const needsSync = localStorage.getItem('atm_needs_sync_' + String(game.id)) === 'true';
            if (needsSync) {
                btnRefresh.classList.add('heartbeat-neon-red', 'btn-needs-sync');
            } else {
                btnRefresh.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
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
                    btnRefresh.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
                    const gameId = currentGame.id;
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
                            localStorage.removeItem('atm_needs_sync_' + gameId);
                            if (window.ATM.events) window.ATM.events.publish('cache:synced', { gameId: gameId });
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
        
        const tabs = [tabEditor, tabGlossary, tabTm, tabAudit, tabExtract];
        function setActiveTab(activeTab) {
            tabs.forEach(t => { if(t) t.classList.remove('active'); });
            if(activeTab) activeTab.classList.add('active');
        }

        if (tabEditor) {
            tabEditor.addEventListener('click', async () => {
                if (window.ATM.Editor && window.ATM.Editor.confirmDiscard && !(await window.ATM.Editor.confirmDiscard())) return;
                setActiveTab(tabEditor);
                startEditor(game.id);
            });
        }
        if (tabGlossary) {
            tabGlossary.addEventListener('click', async () => {
                if (window.ATM.Editor && window.ATM.Editor.confirmDiscard && !(await window.ATM.Editor.confirmDiscard())) return;
                setActiveTab(tabGlossary);
                if(window.ATM.Glossary) window.ATM.Glossary.open(game.id);
            });
        }
        if (tabTm) {
            tabTm.addEventListener('click', async () => {
                if (window.ATM.Editor && window.ATM.Editor.confirmDiscard && !(await window.ATM.Editor.confirmDiscard())) return;
                setActiveTab(tabTm);
                if(window.ATM.Modals) window.ATM.Modals.open('translation-memory-modal');
            });
        }
        
        if (['Bakin'].includes(game.engine)) {
            if (tabAudit) {
                tabAudit.style.display = 'block';
                tabAudit.addEventListener('click', async () => {
                    if (window.ATM.Editor && window.ATM.Editor.confirmDiscard && !(await window.ATM.Editor.confirmDiscard())) return;
                    window.ATM.Workspace.auditCoverage(game.id, game.engine);
                });
            }
            if (tabExtract) {
                tabExtract.style.display = 'block';
                tabExtract.addEventListener('click', async () => {
                    if (window.ATM.Editor && window.ATM.Editor.confirmDiscard && !(await window.ATM.Editor.confirmDiscard())) return;
                    window.ATM.Workspace.runExtractJob(game.id);
                });
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
        const initState = (card && card.dataset.state) ? card.dataset.state : (game.runtime_state || '');
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
                statusText.style.color = 'var(--text-muted)';
                percentText.style.color = 'var(--text-muted)';
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

    async function leave() {
        if (window.ATM.Editor && window.ATM.Editor.confirmDiscard) {
            if (!(await window.ATM.Editor.confirmDiscard())) return;
        }
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
            if (payload && payload.gameId && currentGame && String(payload.gameId) !== String(currentGame.id)) return;
            const btn = document.querySelector('.btn-refresh-workspace');
            if (btn) btn.classList.add('heartbeat-neon-red', 'btn-needs-sync');
        });
        
        window.ATM.events.subscribe('cache:updated', (payload) => {
            const gId = (payload && payload.gameId) ? payload.gameId : (currentGame ? currentGame.id : null);
            if (gId) {
                localStorage.setItem('atm_needs_sync_' + gId, 'true');
            }
            if (payload && payload.gameId && currentGame && String(payload.gameId) !== String(currentGame.id)) return;
            const btn = document.querySelector('.btn-refresh-workspace');
            if (btn) btn.classList.add('heartbeat-neon-red', 'btn-needs-sync');
        });
        
        window.ATM.events.subscribe('cache:cleared', () => {
            if (currentGame) {
                localStorage.removeItem('atm_needs_sync_' + currentGame.id);
                const btn = document.querySelector('.btn-refresh-workspace');
                if (btn) btn.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
                startEditor(currentGame.id);
            }
        });
        
        window.ATM.events.subscribe('editor:reload', (payload) => {
            if (currentGame && (!payload || !payload.gameId || String(payload.gameId) === String(currentGame.id))) {
                startEditor(currentGame.id);
            }
        });
        
        // Listen for sync flag changes from other tabs
        window.addEventListener('storage', (e) => {
            if (e.key && currentGame && e.key === 'atm_needs_sync_' + currentGame.id) {
                const btn = document.querySelector('.btn-refresh-workspace');
                if (btn) {
                    if (e.newValue === 'true') {
                        btn.classList.add('heartbeat-neon-red', 'btn-needs-sync');
                    } else if (e.newValue === null) {
                        btn.classList.remove('heartbeat-neon-red', 'btn-needs-sync');
                    }
                }
            }
        });
        
        // We defer attaching the flag to window.ATM.Workspace below
    }

    async function auditCoverage(gameId, engine) {
        try {
            const res = await window.ATM.api.get(`engines/coverage?game_id=${gameId}`);
            const data = res;
            const title = window.ATM.i18n ? window.ATM.i18n.t('workspace.coverage_title', { engine }) : `${engine} Coverage Report`;
            const stats = window.ATM.i18n ? window.ATM.i18n.t('workspace.coverage_stats', {
                total: data.total,
                translated: data.translated,
                untranslated: data.untranslated,
                coverage: data.coverage_percent
            }) : `Total: ${data.total}\nTranslated: ${data.translated}\nUntranslated: ${data.untranslated}\nCoverage: ${data.coverage_percent}%`;
            window.ATM.Modals.info(title, stats);
        } catch (e) {
            const errMsg = window.ATM.i18n ? window.ATM.i18n.t('workspace.audit_failed', { engine }) : `Failed to audit ${engine} coverage.`;
            window.ATM.Toast.show(errMsg, "error");
        }
    }

    async function runExtractJob(gameId) {
        try {
            const res = await window.ATM.api.post('jobs/extract', { game_id: gameId });
            if (res.error || res.status === 'error') {
                const i18n = window.ATM.i18n;
                const msg = (res.code && i18n ? i18n.t(res.code) : null)
                    || (res.error && i18n ? i18n.t(res.error) : null)
                    || res.error
                    || (i18n ? i18n.t('workspace.extract_start_error') : 'Extract error');
                window.ATM.Toast.show(msg, "error");
                return;
            }
            if (res.status === 'already_running') {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('workspace.job_already_running') : 'Job is already running!';
                window.ATM.Toast.show(msg, 'info');
            } else {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('workspace.extract_started') : 'Extract job started.';
                window.ATM.Toast.show(msg, 'success');
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
                            if (textEl) textEl.textContent = window.ATM.i18n ? window.ATM.i18n.t('status.completed') : 'Completed';
                            if (barEl) barEl.style.width = '100%';
                            setTimeout(() => { if (container) container.style.display = 'none'; }, 3000);
                            const msg = window.ATM.i18n ? window.ATM.i18n.t('workspace.extract_completed') : 'Extract job completed!';
                            window.ATM.Toast.show(msg, 'success');
                        } else if (status.status === 'failed' || status.status === 'cancelled') {
                            if (textEl) textEl.textContent = status.status;
                            setTimeout(() => { if (container) container.style.display = 'none'; }, 3000);
                            const msg = window.ATM.i18n ? window.ATM.i18n.t('workspace.extract_failed', { status: status.status }) : `Extract job ${status.status}`;
                            window.ATM.Toast.show(msg, 'error');
                        }
                    }
                );
            }
        } catch (e) {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('workspace.extract_start_error') : 'Failed to start extract job.';
            window.ATM.Toast.show(msg, 'error');
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

