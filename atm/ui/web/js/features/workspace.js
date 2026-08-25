window.ATM = window.ATM || {};
window.ATM.features = window.ATM.features || {};

/**
 * ATM.Workspace
 * Architecture Rule 6: Manage Lifecycle (open, mount, leave, destroy)
 */
(function() {
    let currentGame = null;

    function open(gameId) {
        if (window.ATM.navigation) {
            window.ATM.navigation.showWorkspace(gameId);
        }
        
        // Fetch game details to show in header
        window.ATM.api.get(`games`)
            .then(data => {
                const game = data.games.find(g => g.id === gameId);
                if (game) {
                    currentGame = game;
                    document.getElementById('workspace-title').textContent = game.game_name || 'Unknown Game';
                    document.getElementById('workspace-subtitle').textContent = `Engine: ${game.engine || 'Unknown'} | Translator: ${game.translator || 'Google'}`;
                    
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
        startEditor(game.id);
    }

    function startEditor(gameId) {
        const mountPoint = document.getElementById('editor-workspace-mount');
        const template = document.getElementById('workspace-editor-template');
        
        if (mountPoint && template) {
            mountPoint.replaceChildren(template.content.cloneNode(true));
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
        if (window.ATM.navigation) {
            window.ATM.navigation.showLibrary();
        }
    }

    // Init listeners (script is deferred, so DOM is ready)
    const backBtn = document.getElementById('workspace-back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', leave);
    }

    async function auditCoverage(gameId, engine) {
        try {
            const res = await window.ATM.api.get(`engines/coverage?game_id=${gameId}`);
            const data = res;
            window.ATM.Modals.info(`${engine} Coverage Report`, 
                `Total Strings: ${data.total}\nTranslated: ${data.translated}\nUntranslated: ${data.untranslated}\nCoverage: ${data.coverage_percent}%`);
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
        open,
        auditCoverage,
        runExtractJob,
        leave,
        mount,
        startEditor
    };
})();

