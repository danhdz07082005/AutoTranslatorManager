window.ATM = window.ATM || {};

window.ATM.Editor = (function() {
    let currentGameId = null;
    let currentPage = 1;
    let currentLimit = 50;
    let currentQuery = "";
    let currentFilter = "all";
    let entries = [];
    let qaFindings = {};
    let conflictStates = {};
    let _delegationSetup = false;
    
    // TASK 5.3: Draft Persistence state
    let drafts = {}; // { entryId: draftTranslated }

    let searchDebounceTimer;
    let fetchController = null;
    
    const validatePlaceholders = (original, translated) => {
        const regex = /(\{\d+\}|\[\d+\]|%\w+)/g;
        const origMatches = original.match(regex) || [];
        const transMatches = translated.match(regex) || [];
        const missing = [];
        origMatches.forEach(m => {
            if (!transMatches.includes(m)) missing.push(m);
        });
        return missing;
    };
    
    // TASK 5.3: Load drafts
    const loadDrafts = () => {
        if (!currentGameId) return;
        const saved = localStorage.getItem(`atm_drafts_${currentGameId}`);
        if (saved) {
            try { drafts = JSON.parse(saved); } catch(e) { drafts = {}; }
        } else {
            drafts = {};
        }
    };
    
    const saveDrafts = () => {
        if (!currentGameId) return;
        if (Object.keys(drafts).length === 0) {
            localStorage.removeItem(`atm_drafts_${currentGameId}`);
        } else {
            localStorage.setItem(`atm_drafts_${currentGameId}`, JSON.stringify(drafts));
        }
    };
    
    const updateDraft = (entryId, val, originalVal) => {
        if (val === originalVal) {
            delete drafts[entryId];
        } else {
            drafts[entryId] = val;
        }
        saveDrafts();
    };

    // TASK 5.1 & 5.2: Unsaved changes tracking
    const hasUnsavedChanges = () => {
        return Object.keys(drafts).length > 0;
    };

    const confirmDiscard = async () => {
        if (!hasUnsavedChanges()) return true;
        
        return new Promise((resolve) => {
            const msg = window.ATM.i18n ? window.ATM.i18n.t('editor.confirm_discard', 'Bạn có thay đổi chưa lưu. Bạn muốn làm gì?') : 'You have unsaved changes. What would you like to do?';
            if (window.ATM.Modals && window.ATM.Modals.confirmSave) {
                window.ATM.Modals.confirmSave(msg).then(async (action) => {
                    if (action === 'save') {
                        await saveBatchEdits();
                        resolve(true); // allow navigation
                    } else if (action === 'discard') {
                        drafts = {};
                        saveDrafts();
                        updateMasterButtons();
                        resolve(true); // allow navigation
                    } else {
                        resolve(false); // abort navigation
                    }
                });
            } else {
                const agreed = confirm(msg);
                if (agreed) {
                    saveBatchEdits().then(() => resolve(true));
                } else {
                    resolve(false);
                }
            }
        });
    };
    
    // Check before leaving editor via ATM.Workspace hooks or navigation
    window.ATM.canLeaveEditor = () => {
        if (hasUnsavedChanges()) {
            return false;
        }
        return true;
    };
    
    // TASK 5.2: beforeunload
    window.addEventListener('beforeunload', (e) => {
        if (hasUnsavedChanges()) {
            e.preventDefault();
            e.returnValue = ''; // Standard way to show prompt
        }
    });

    const init = () => {
        if (_delegationSetup) return;
        _delegationSetup = true;

        const container = document.getElementById('workspace-container');
        if (!container) return;
        
        container.addEventListener('click', async (e) => {
            if (e.target.closest('#editor-run-qa-btn')) {
                runQA();
            } else if (e.target.closest('#editor-prev-page')) {
                if (currentPage > 1) {
                    if (await confirmDiscard()) {
                        currentPage--;
                        fetchData();
                    }
                }
            } else if (e.target.closest('#editor-next-page')) {
                if (await confirmDiscard()) {
                    currentPage++;
                    fetchData();
                }
            } else if (e.target.closest('#editor-master-save-btn')) {
                saveBatchEdits();
            } else if (e.target.closest('#editor-master-cancel-btn')) {
                drafts = {};
                saveDrafts();
                updateMasterButtons();
                renderList();
            }
        });

        container.addEventListener('input', (e) => {
            if (e.target.id === 'editor-search') {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(async () => {
                    if (hasUnsavedChanges()) {
                        if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('editor.search_draft_warning', 'Vui lòng lưu hoặc hủy thay đổi trước khi tìm kiếm'), 'warning');
                        e.target.value = currentQuery;
                        return;
                    }
                    currentQuery = e.target.value.trim();
                    currentPage = 1;
                    fetchData();
                }, 300);
            }
        });

        container.addEventListener('change', async (e) => {
            if (e.target.id === 'editor-filter-type') {
                if (await confirmDiscard()) {
                    currentFilter = e.target.value;
                    renderList();
                } else {
                    // Revert select
                    e.target.value = currentFilter;
                }
            }
        });
    };
    
    const updateMasterButtons = () => {
        const saveBtn = document.getElementById('editor-master-save-btn');
        const cancelBtn = document.getElementById('editor-master-cancel-btn');
        if (!saveBtn || !cancelBtn) return;
        
        let dirtyCount = Object.keys(drafts).length;
        if (dirtyCount > 0) {
            saveBtn.style.display = 'flex';
            saveBtn.classList.remove('hidden');
            cancelBtn.style.display = 'flex';
            cancelBtn.classList.remove('hidden');
            const saveText = document.getElementById('editor-master-save-text');
            if (saveText) {
                saveText.textContent = dirtyCount.toString();
            }
        } else {
            saveBtn.style.display = 'none';
            saveBtn.classList.add('hidden');
            cancelBtn.style.display = 'none';
            cancelBtn.classList.add('hidden');
        }
    };

    const open = (gameId) => {
        currentGameId = gameId;
        currentPage = 1;
        currentQuery = "";
        currentFilter = "all";
        qaFindings = {};
        conflictStates = {};
        
        loadDrafts(); // TASK 5.3: Load drafts on open
        
        const searchInput = document.getElementById('editor-search');
        if (searchInput) searchInput.value = "";
        fetchData();
    };

    const fetchData = async () => {
        if (fetchController) fetchController.abort();
        fetchController = new AbortController();

        try {
            const listEl = document.getElementById('editor-list');
            if (!listEl) return;
            
            while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
            
            for(let i=0; i<5; i++) {
                const skeleton = document.createElement('div');
                skeleton.className = 'skeleton-row';
                skeleton.style.height = '80px';
                skeleton.style.background = 'linear-gradient(90deg, var(--bg-card) 25%, var(--bg-hover) 50%, var(--bg-card) 75%)';
                skeleton.style.backgroundSize = '200% 100%';
                skeleton.style.animation = 'skeleton-loading 1.5s infinite';
                skeleton.style.borderRadius = '6px';
                skeleton.style.marginBottom = '12px';
                listEl.appendChild(skeleton);
            }
            
            const res = await window.ATM.api.get(`games/${encodeURIComponent(currentGameId)}/translations?query=${encodeURIComponent(currentQuery)}&page=${currentPage}&limit=${currentLimit}`, {
                signal: fetchController.signal
            });
            
            while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
            
            if (res.status === 'success') {
                entries = res.data.items || [];
                const total = res.data.total || 0;
                
                const statsEl = document.getElementById('editor-stats');
                if (statsEl) {
                    const fallback = `Total: ${total} items`;
                    const translated = window.ATM.i18n ? window.ATM.i18n.t('editor.total_items', { total: total }) : fallback;
                    statsEl.textContent = translated || fallback;
                }
                
                const maxPage = Math.ceil(total / currentLimit) || 1;
                
                const pageLabel = document.getElementById('editor-page-label');
                if (pageLabel) pageLabel.textContent = `${currentPage} / ${maxPage}`;
                
                const prevBtn = document.getElementById('editor-prev-page');
                const nextBtn = document.getElementById('editor-next-page');
                if (prevBtn) prevBtn.disabled = currentPage <= 1;
                if (nextBtn) nextBtn.disabled = currentPage >= maxPage;
                
                qaFindings = {};
                conflictStates = {};
                renderList();
            } else {
                entries = [];
                renderList();
                if (window.ATM.Toast && res && res.error) {
                    window.ATM.Toast.show(res.error, "error");
                }
            }
        } catch (e) {
            if (e.name !== 'NetworkError' && e.name !== '') {
                console.error(e);
                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t("editor.error_load", "Error loading data"), true);
            }
        }
    };

    const runQA = async () => {
        if (!entries || entries.length === 0) {
            if (window.ATM.Toast) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('editor.qa_no_entries') : 'No translation lines available for QA scanning!';
                window.ATM.Toast.show(msg, 'info');
            }
            return;
        }

        const hasTranslations = entries.some(e => {
            const tr = drafts[e.id] !== undefined ? drafts[e.id] : e.translated;
            return tr && String(tr).trim().length > 0;
        });

        if (!hasTranslations) {
            if (window.ATM.Toast) {
                const msg = window.ATM.i18n ? window.ATM.i18n.t('editor.qa_no_translations') : 'No translated lines found yet. Please translate before running QA!';
                window.ATM.Toast.show(msg, 'info');
            }
            return;
        }
        try {
            const btn = document.getElementById('editor-run-qa-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> ' + (window.ATM.i18n.t('editor.qa_running') || '');
            btn.disabled = true;

            const payload = entries.map(e => ({
                id: e.id,
                source: e.original,
                translated: drafts[e.id] !== undefined ? drafts[e.id] : e.translated
            }));
            const res = await window.ATM.api.post('cache/qa-review', {
                entries: payload
            });

            if (res.status === 'success') {
                const backendFindings = res.data.findings || res.data || {};
                qaFindings = {};
                
                // Remap backend findings (keyed by entry ID or original) to ID-based findings for frontend rendering
                for (const e of entries) {
                    const rawFinding = backendFindings[e.id] || backendFindings[String(e.id)] || backendFindings[e.original];
                    if (rawFinding) {
                        const finding = Array.isArray(rawFinding) ? rawFinding[0] : rawFinding;
                        if (finding) {
                            qaFindings[e.id] = finding;
                        }
                    }
                }
                
                renderList();
                const count = Object.keys(qaFindings).length;
                if (window.ATM.Toast) {
                    if (count > 0) {
                        const template = window.ATM.i18n ? window.ATM.i18n.t('editor.qa_found') : 'Phát hiện {count} lỗi QA!';
                        const msg = template.replace('{count}', count);
                        window.ATM.Toast.show(msg, "warning");
                    } else {
                        const msg = window.ATM.i18n ? window.ATM.i18n.t('editor.qa_clean') : 'Tuyệt vời! Không phát hiện lỗi QA nào.';
                        window.ATM.Toast.show(msg, "success");
                    }
                }
            } else if (window.ATM.Toast) {
                const i18n = window.ATM.i18n;
                const errMsg = (res && res.code && i18n ? i18n.t(res.code) : null)
                    || (res && res.error && i18n ? i18n.t(res.error) : null)
                    || (res ? res.error : null)
                    || (i18n ? i18n.t('editor.qa_error') : "Lỗi khi chạy QA");
                window.ATM.Toast.show(errMsg, "error");
            }
            btn.innerHTML = originalText;
            btn.disabled = false;
        } catch (e) {
            console.error("QA error:", e);
            if (window.ATM.Toast) {
                const errMsg = window.ATM.i18n ? window.ATM.i18n.t('editor.qa_error') : "Lỗi khi chạy QA";
                window.ATM.Toast.show(`${errMsg}: ${e.message}`, "error");
            }
            const btn = document.getElementById('editor-run-qa-btn');
            if (btn) {
                btn.innerHTML = '<span data-i18n="editor.run_qa">QA Scanner</span>';
                if (window.ATM.i18n) window.ATM.i18n.updateDOM(btn);
                btn.disabled = false;
            }
        }
    };
    
    const saveRow = async (entry, inputEl, rowEl, actionsEl, retryBtn, saveBtn, cancelBtn) => {
        const newValue = inputEl.value;
        if (newValue === entry.translated && !conflictStates[entry.id]) {
            actionsEl.style.display = 'none';
            return;
        }
        
        try {
            inputEl.disabled = true;
            saveBtn.innerHTML = '<span class="spinner" style="width:12px;height:12px;display:inline-block"></span>';
            saveBtn.disabled = true;
            cancelBtn.disabled = true;
            
            const res = await window.ATM.api.post(`games/${encodeURIComponent(currentGameId)}/translations/${entry.id}/update`, {
                translated: newValue,
                version: entry.version
            });
            
            if (res.status === 'success') {
                entry.translated = newValue;
                entry.version = res.version;
                actionsEl.style.display = 'none';
                
                updateDraft(entry.id, newValue, newValue); 
                updateMasterButtons();
                
                if (window.ATM.events) {
                    window.ATM.events.publish('cache:updated', { gameId: currentGameId });
                }
                
                if (conflictStates[entry.id]) {
                    delete conflictStates[entry.id];
                    const qaBox = rowEl.querySelector('.qa-box');
                    if (qaBox) qaBox.remove();
                    rowEl.style.borderColor = 'var(--border-color)';
                    rowEl.style.boxShadow = 'none';
                }
                
                retryBtn.style.display = 'none';
                saveBtn.style.display = 'block';
            } else if (res.status === 'conflict') {
                // Re-enable and show conflict UI
                inputEl.disabled = false;
                cancelBtn.disabled = false;
                
                conflictStates[entry.id] = {
                    serverTranslated: res.server_state.translated,
                    serverVersion: res.server_state.version
                };
                
                rowEl.style.borderColor = 'var(--danger)';
                rowEl.style.boxShadow = '0 0 4px var(--danger)';
                
                saveBtn.style.display = 'none';
                retryBtn.style.display = 'block';
                
                renderConflictUI(entry, inputEl, rowEl, actionsEl, retryBtn, saveBtn, cancelBtn, conflictStates[entry.id]);
                
            } else {
                throw new Error(res.error || "Save failed");
            }
            
        } catch (e) {
            console.error(e);
            inputEl.disabled = false;
            cancelBtn.disabled = false;
            
            saveBtn.style.display = 'none';
            retryBtn.style.display = 'block';
            
            if (window.ATM.Toast) {
                window.ATM.Toast.show(e.message || window.ATM.i18n.t('editor.save_error'), true);
            }
        } finally {
            saveBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            saveBtn.disabled = false;
            inputEl.disabled = false;
            cancelBtn.disabled = false;
        }
    };
    
    const renderConflictUI = (entry, inputEl, rowEl, actionsEl, retryBtn, saveBtn, cancelBtn, state) => {
        const targetCol = inputEl.parentElement;
        
        let qaBox = rowEl.querySelector('.qa-box');
        if (!qaBox) {
            qaBox = document.createElement('div');
            qaBox.className = 'qa-box';
            qaBox.style.borderColor = 'var(--danger)';
        } else {
            while(qaBox.firstChild) qaBox.removeChild(qaBox.firstChild);
            qaBox.style.borderColor = 'var(--danger)';
        }
        
        const msgSpan = document.createElement('span');
        msgSpan.style.color = 'var(--danger)';
        msgSpan.innerHTML = (window.ATM.i18n.t("editor.conflict_msg", "<strong>CONFLICT (Version {v})</strong>: Data changed elsewhere.")).replace('{v}', state.serverVersion);
        qaBox.appendChild(msgSpan);
        
        const diffBox = document.createElement('div');
        diffBox.style.background = 'var(--bg-base)';
        diffBox.style.padding = '6px';
        diffBox.style.borderRadius = '4px';
        diffBox.style.color = 'var(--text-main)';
        diffBox.textContent = state.serverTranslated;
        qaBox.appendChild(diffBox);
        
        const btnRow = document.createElement('div');
        btnRow.style.display = 'flex';
        btnRow.style.gap = '8px';
        
        const keepMineBtn = document.createElement('button');
        keepMineBtn.className = 'btn-secondary';
        keepMineBtn.textContent = window.ATM.i18n.t("editor.keep_mine", "Keep mine (Overwrite)");
        keepMineBtn.onclick = () => {
            entry.version = state.serverVersion;
            delete conflictStates[entry.id];
            qaBox.remove();
            saveBtn.style.display = 'block';
            retryBtn.style.display = 'none';
            rowEl.style.borderColor = 'var(--border-color)';
            rowEl.style.boxShadow = 'none';
            saveRow(entry, inputEl, rowEl, actionsEl, retryBtn, saveBtn, cancelBtn);
        };
        
        const useNewBtn = document.createElement('button');
        useNewBtn.className = 'btn-primary';
        useNewBtn.textContent = window.ATM.i18n.t("editor.use_new", "Use new version");
        useNewBtn.onclick = () => {
            inputEl.value = state.serverTranslated;
            entry.translated = state.serverTranslated;
            entry.version = state.serverVersion;
            
            updateDraft(entry.id, state.serverTranslated, entry.translated);
            
            delete conflictStates[entry.id];
            qaBox.remove();
            actionsEl.style.display = 'none';
            rowEl.style.borderColor = 'var(--border-color)';
            rowEl.style.boxShadow = 'none';
            retryBtn.style.display = 'none';
            saveBtn.style.display = 'block';
        };
        
        btnRow.appendChild(useNewBtn);
        btnRow.appendChild(keepMineBtn);
        qaBox.appendChild(btnRow);
        
        targetCol.appendChild(qaBox);
    };
    
    const saveBatchEdits = async () => {
        const itemsToUpdate = [];
        entries.forEach(entry => {
            const input = document.getElementById(`input-${entry.id}`);
            if (input && input.value !== entry.translated) {
                itemsToUpdate.push({
                    id: entry.id,
                    translated: input.value,
                    version: entry.version
                });
            }
        });
        
        if (itemsToUpdate.length === 0) {
            return;
        }
        
        const saveBtn = document.getElementById('editor-master-save-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> ' + window.ATM.i18n.t('editor.saving', 'Saving...');
        saveBtn.disabled = true;
        
        try {
            const res = await window.ATM.api.post(`games/${encodeURIComponent(currentGameId)}/translations/batch-update`, {
                items: itemsToUpdate
            });
            
            if (res.status === 'success') {
                if (window.ATM.events) {
                    window.ATM.events.publish('cache:updated', { gameId: currentGameId });
                }
                const data = res.data || {};
                const saved = data.saved || [];
                const conflicts = data.conflicts || [];
                const errors = data.errors || [];
                
                saved.forEach(s => {
                    delete drafts[s.id];
                    const entry = entries.find(e => e.id === s.id);
                    if (entry) {
                        entry.translated = s.translated;
                        entry.version = s.version;
                    }
                });
                saveDrafts();
                updateMasterButtons();
                
                conflicts.forEach(c => {
                    conflictStates[c.id] = {
                        serverTranslated: c.server_state.translated,
                        serverVersion: c.server_state.version
                    };
                });
                
                if (conflicts.length > 0 || errors.length > 0) {
                    if (window.ATM.Toast) {
                        const template = window.ATM.i18n ? window.ATM.i18n.t('editor.batch_save_partial') : 'Đã lưu {saved}. Bị lỗi/xung đột: {failed}. Vui lòng thử lại.';
                        const msg = template.replace('{saved}', saved.length).replace('{failed}', conflicts.length + errors.length);
                        window.ATM.Toast.show(msg, "warning");
                    }
                }
                renderList(); 
            } else {
                throw new Error(res.error || "Batch update failed");
            }
        } catch (e) {
            console.error(e);
            if (window.ATM.Toast) window.ATM.Toast.show(e.message || window.ATM.i18n.t("editor.network_error", "Network error or data conflict"), true);
        } finally {
            saveBtn.innerHTML = originalText;
            saveBtn.disabled = false;
        }
    };

    const renderList = () => {
        const listEl = document.getElementById('editor-list');
        if (!listEl) return;
        while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
        
        let displayEntries = entries;
        if (currentFilter === 'qa_error') {
            displayEntries = entries.filter(e => qaFindings[e.id]);
        }

        if (displayEntries.length === 0) {
            const div = document.createElement('div');
            div.style.textAlign = 'center';
            div.style.padding = '20px';
            div.style.color = 'var(--text-muted)';
            div.textContent = window.ATM.i18n.t('editor.empty');
            listEl.appendChild(div);
            return;
        }

        displayEntries.forEach(entry => {
            const row = document.createElement('div');
            row.id = `row-${entry.id}`;
            row.style.display = 'flex';
            row.style.gap = '16px';
            row.style.padding = '8px';
            row.style.background = 'var(--bg-card)';
            row.style.borderRadius = '6px';
            row.style.border = '1px solid var(--border-color)';
            row.style.transition = 'all 0.2s';
            
            const rawFinding = qaFindings[entry.id];
            const finding = Array.isArray(rawFinding) ? rawFinding[0] : rawFinding;
            if (finding) {
                const severity = (finding.severity || 'warning').toLowerCase();
                if (severity === 'error') {
                    row.style.borderColor = 'var(--danger)';
                    row.style.boxShadow = '0 0 0 1px var(--danger)';
                } else {
                    row.style.borderColor = 'var(--warning)';
                    row.style.boxShadow = '0 0 0 1px var(--warning)';
                }
            }

            const sourceCol = document.createElement('div');
            sourceCol.style.flex = '1';
            sourceCol.style.fontSize = '13px';
            sourceCol.style.padding = '8px';
            sourceCol.style.background = 'var(--bg-base)';
            sourceCol.style.borderRadius = '4px';
            sourceCol.style.whiteSpace = 'pre-wrap';
            sourceCol.style.wordBreak = 'break-word';
            sourceCol.textContent = entry.original;
            
            const targetCol = document.createElement('div');
            targetCol.style.flex = '1';
            targetCol.style.display = 'flex';
            targetCol.style.flexDirection = 'column';
            targetCol.style.gap = '8px';

            const input = document.createElement('textarea');
            input.id = `input-${entry.id}`;
            
            // TASK 5.3: Load draft if exists
            if (drafts[entry.id] !== undefined) {
                input.value = drafts[entry.id];
            } else {
                input.value = entry.translated;
            }
            
            input.className = 'themed-input';
            input.style.width = '100%';
            input.style.minHeight = '60px';
            input.style.padding = '8px';
            input.style.fontSize = '13px';
            input.style.resize = 'vertical';
            
            const actions = document.createElement('div');
            actions.className = 'row-actions';
            
            // If draft loaded and differs from original, show actions immediately
            if (drafts[entry.id] !== undefined && drafts[entry.id] !== entry.translated) {
                actions.style.display = 'flex';
                input.style.borderColor = 'var(--warning)';
            } else {
                actions.style.display = 'none';
            }
            
            actions.style.justifyContent = 'flex-end';
            actions.style.gap = '8px';
            actions.style.flexDirection = 'column'; // Stack vertically on the right
            
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn-delete heartbeat-neon-red';
            cancelBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
            cancelBtn.style.padding = '8px';
            
            const retryBtn = document.createElement('button');
            retryBtn.className = 'btn-secondary heartbeat-neon-orange';
            retryBtn.style.display = 'none';
            retryBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>';
            retryBtn.style.padding = '6px';
            
            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn-success heartbeat-neon-green';
            saveBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>';
            saveBtn.style.padding = '8px';
            
            actions.appendChild(saveBtn);
            actions.appendChild(retryBtn);
            actions.appendChild(cancelBtn);
            
            const validationBox = document.createElement('div');
            validationBox.style.fontSize = '12px';
            validationBox.style.color = 'var(--danger)';
            validationBox.style.display = 'none';
            validationBox.style.marginTop = '-4px';

            const inputRow = document.createElement('div');
            inputRow.style.display = 'flex';
            inputRow.style.gap = '8px';
            inputRow.style.alignItems = 'flex-start';
            inputRow.style.width = '100%';
            
            input.style.flex = '1';
            
            inputRow.appendChild(input);
            inputRow.appendChild(actions);
            
            input.addEventListener('focus', () => {
                actions.style.display = 'flex';
            });
            
            input.addEventListener('input', () => {
                updateDraft(entry.id, input.value, entry.translated);
                updateMasterButtons();
                
                const missing = validatePlaceholders(entry.original, input.value);
                if (missing.length > 0) {
                    validationBox.textContent = (window.ATM.i18n.t('editor.missing_vars', '⚠️ Warning: Missing vars {vars}')).replace('{vars}', missing.join(', '));
                    validationBox.style.display = 'block';
                    input.style.borderColor = 'var(--danger)';
                } else {
                    validationBox.style.display = 'none';
                    input.style.borderColor = 'var(--border-color)';
                }
            });
            
            input.addEventListener('blur', () => {
                if (input.value === entry.translated && !conflictStates[entry.id]) {
                    actions.style.display = 'none';
                    validationBox.style.display = 'none';
                    input.style.borderColor = 'var(--border-color)';
                }
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    saveRow(entry, input, row, actions, retryBtn, saveBtn, cancelBtn);
                } else if (e.key === 'Escape') {
                    if (conflictStates[entry.id]) return;
                    
                    input.value = entry.translated;
                    updateDraft(entry.id, input.value, entry.translated);
                    validationBox.style.display = 'none';
                    input.style.borderColor = 'var(--border-color)';
                    actions.style.display = 'none';
                    updateMasterButtons();
                }
            });
            
            cancelBtn.addEventListener('click', () => {
                input.value = entry.translated;
                updateDraft(entry.id, input.value, entry.translated);
                actions.style.display = 'none';
                updateMasterButtons();
                
                validationBox.style.display = 'none';
                input.style.borderColor = 'var(--border-color)';
                row.style.borderColor = 'var(--border-color)';
                row.style.boxShadow = 'none';
                retryBtn.style.display = 'none';
                saveBtn.style.display = 'block';
                
                if (conflictStates[entry.id]) {
                    delete conflictStates[entry.id];
                    const qaBox = row.querySelector('.qa-box');
                    if (qaBox) qaBox.remove();
                }
            });
            
            saveBtn.addEventListener('click', () => saveRow(entry, input, row, actions, retryBtn, saveBtn, cancelBtn));
            retryBtn.addEventListener('click', () => saveRow(entry, input, row, actions, retryBtn, saveBtn, cancelBtn));

            targetCol.appendChild(inputRow);
            targetCol.appendChild(validationBox);

            if (finding) {
                const qaBox = document.createElement('div');
                qaBox.className = 'qa-box';
                qaBox.style.fontSize = '12px';
                qaBox.style.padding = '6px';
                qaBox.style.borderRadius = '4px';
                qaBox.style.display = 'flex';
                qaBox.style.flexDirection = 'column';
                qaBox.style.gap = '4px';
                
                const severity = (finding.severity || 'warning').toLowerCase();
                if (severity === 'error') {
                    qaBox.style.background = 'rgba(239, 68, 68, 0.1)';
                    qaBox.style.color = 'var(--danger)';
                } else {
                    qaBox.style.background = 'rgba(245, 158, 11, 0.1)';
                    qaBox.style.color = 'var(--warning)';
                }

                const msgSpan = document.createElement('div');
                const strong = document.createElement('strong');
                strong.textContent = `QA ${severity.toUpperCase()}`;
                msgSpan.appendChild(strong);
                msgSpan.appendChild(document.createTextNode(`: ${finding.message || ''} `));
                qaBox.appendChild(msgSpan);
                targetCol.appendChild(qaBox);
            }

            if (conflictStates[entry.id]) {
                input.disabled = false;
                cancelBtn.disabled = false;
                row.style.borderColor = 'var(--danger)';
                row.style.boxShadow = '0 0 4px var(--danger)';
                saveBtn.style.display = 'none';
                retryBtn.style.display = 'block';
                actions.style.display = 'flex';
                renderConflictUI(entry, input, row, actions, retryBtn, saveBtn, cancelBtn, conflictStates[entry.id]);
            }

            row.appendChild(sourceCol);
            row.appendChild(targetCol);
            listEl.appendChild(row);
        });
    };

    const close = () => {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        // We do not clear drafts here, so they are kept when user goes back and forth
        currentGameId = null;
    };

    return { init, open, close, confirmDiscard };
})();
