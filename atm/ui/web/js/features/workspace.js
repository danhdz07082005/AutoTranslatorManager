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
        
        container.innerHTML = `
            <div style="padding: 20px; display:flex; flex-direction:column; height: 100%;">
                <div class="workspace-tabs" style="display:flex; border-bottom: 1px solid var(--border-color); margin-bottom: 20px;">
                    <button class="tab-btn active" style="padding: 12px 20px; background: transparent; border: none; border-bottom: 2px solid var(--accent); color: var(--accent); font-weight: 600; cursor: pointer;">Editor</button>
                    <button class="tab-btn" style="padding: 12px 20px; background: transparent; border: none; color: var(--text-secondary); cursor: pointer;" onclick="if(window.ATM.Glossary) window.ATM.Glossary.open('${game.id}')">Thuật ngữ (Glossary)</button>
                    <button class="tab-btn" style="padding: 12px 20px; background: transparent; border: none; color: var(--text-secondary); cursor: pointer;" onclick="if(window.ATM.Modals) window.ATM.Modals.open('translation-memory-modal')">Bộ nhớ dịch (TM)</button>
                    ${['Bakin', 'RenPy', 'RPG Maker'].includes(game.engine) ? `<button class="tab-btn" style="padding: 12px 20px; background: transparent; border: none; color: var(--accent); cursor: pointer; font-weight:bold;" onclick="window.ATM.Workspace.auditCoverage('${game.id}', '${game.engine}')">🔍 Coverage Audit</button>` : ''}
                    ${['Bakin', 'RenPy', 'RPG Maker'].includes(game.engine) ? `<button class="tab-btn" style="padding: 12px 20px; background: transparent; border: none; color: var(--accent); cursor: pointer; font-weight:bold;" onclick="window.ATM.Workspace.runExtractJob('${game.id}')">📦 Extract Offline</button>` : ''}
                    <div id="job-progress-container-${game.id}" style="display:none; padding: 12px 20px; align-items:center;">
                        <span id="job-progress-text-${game.id}" style="margin-right: 10px; font-size: 0.9em; color: var(--text-secondary);"></span>
                        <div style="width: 150px; height: 8px; background: var(--surface-200); border-radius: 4px; overflow: hidden;">
                            <div id="job-progress-bar-${game.id}" style="width: 0%; height: 100%; background: var(--accent); transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                </div>
                <div id="editor-workspace-mount" style="flex: 1; overflow: hidden; display:flex; flex-direction:column;">
                    <!-- Editor mounts here -->
                </div>
            </div>
        `;

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
        if (container) container.innerHTML = ''; // Clean up memory
    }

    function leave() {
        cleanup();
        if (window.ATM.navigation) {
            window.ATM.navigation.showLibrary();
        }
    }

    // Init listeners
    document.addEventListener('DOMContentLoaded', () => {
        const backBtn = document.getElementById('workspace-back-btn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                leave();
            });
        }
    });

    async function auditCoverage(gameId, engine) {
        try {
            const res = await window.ATM.api.get(`engines/coverage?game_id=${gameId}`);
            alert(`${engine} Coverage Report:\nTotal Strings: ${res.total}\nTranslated: ${res.translated}\nUntranslated: ${res.untranslated}\nCoverage: ${res.coverage_percent}%`);
        } catch (e) {
            alert(`Failed to audit ${engine} coverage.`);
        }
    }

    async function runExtractJob(gameId) {
        try {
            const res = await window.ATM.api.post('jobs/extract', { game_id: gameId });
            if (res.error) {
                alert(res.error);
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
",



