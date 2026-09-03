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
    let isBatchEditing = false;
    
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
            const msg = window.ATM.i18n ? window.ATM.i18n.t('editor.confirm_discard', '') : '';
            if (window.ATM.Modals && window.ATM.Modals.confirm) {
                window.ATM.Modals.confirm(msg).then(agreed => {
                    if (agreed) {
                        drafts = {};
                        saveDrafts();
                    }
                    resolve(agreed);
                });
            } else {
                const agreed = confirm(msg);
                if (agreed) {
                    drafts = {};
                    saveDrafts();
                }
                resolve(agreed);
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
            } else if (e.target.closest('#editor-search-btn')) {
                if (await confirmDiscard()) {
                    const searchInput = document.getElementById('editor-search');
                    if (searchInput) {
                        currentQuery = searchInput.value.trim();
                        currentPage = 1;
                        fetchData();
                    }
                }
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
            } else if (e.target.closest('#editor-batch-edit-btn')) {
                toggleBatchEdit(true);
            } else if (e.target.closest('#editor-batch-save-btn')) {
                saveBatchEdits();
            }
        });

        container.addEventListener('input', (e) => {
            if (e.target.id === 'editor-search') {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(async () => {
                    if (await confirmDiscard()) {
                        currentQuery = e.target.value.trim();
                        currentPage = 1;
                        fetchData();
                    }
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
    
    const toggleBatchEdit = (enable) => {
        isBatchEditing = enable;
        const editBtn = document.getElementById('editor-batch-edit-btn');
        const saveBtn = document.getElementById('editor-batch-save-btn');
        
        if (enable) {
            editBtn.style.display = 'none';
            saveBtn.style.display = 'flex';
            saveBtn.classList.remove('hidden');
            document.querySelectorAll('.row-actions').forEach(el => el.style.display = 'none');
            updateBatchSaveButtonText();
        } else {
            editBtn.style.display = 'flex';
            saveBtn.style.display = 'none';
            saveBtn.classList.add('hidden');
        }
    };
    
    const updateBatchSaveButtonText = () => {
        if (!isBatchEditing) return;
        let dirtyCount = Object.keys(drafts).length;
        const saveText = document.getElementById('editor-batch-save-text');
        if (saveText) saveText.textContent = '';
    };

    const open = (gameId) => {
        currentGameId = gameId;
        currentPage = 1;
        currentQuery = "";
        currentFilter = "all";
        qaFindings = {};
        conflictStates = {};
        isBatchEditing = false;
        
        loadDrafts(); // TASK 5.3: Load drafts on open
        
        const searchInput = document.getElementById('editor-search');
        if (searchInput) searchInput.value = "";
        
        toggleBatchEdit(false);
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
                isBatchEditing = false;
                toggleBatchEdit(false);
                renderList();
            }
        } catch (e) {
            if (e.name !== 'NetworkError' && e.name !== '') {
                console.error(e);
                if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t("editor.error_load", "Error loading data"), true);
            }
        }
    };

    const runQA = async () => {
        if (!entries || entries.length === 0) return;
        try {
            const btn = document.getElementById('editor-run-qa-btn');
            const originalText = btn.innerHTML;
            btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> ' + (window.ATM.i18n.t('editor.qa_running') || '');
            btn.disabled = true;

            // Send entry.id and entry.original
            const payload = entries.map(e => ({ id: e.id, original: e.original, translated: e.translated }));
            const res = await window.ATM.api.post('cache/qa-review', {
                entries: payload
            });

            if (res.status === 'success') {
                // TASK 7.1: QA theo line_id
                // Assuming backend QA returns { "id": finding } or we just map it here
                // If backend still returns { "original": finding }, we need to remap it to ID.
                const backendFindings = res.data.findings || res.data || {};
                qaFindings = {};
                
                // Remap original-based findings to ID-based findings for frontend rendering
                for (const e of entries) {
                    if (backendFindings[e.original]) {
                        qaFindings[e.id] = backendFindings[e.original];
                    }
                }
                
                renderList();
            }
            btn.innerHTML = originalText;
            btn.disabled = false;
        } catch (e) {
            console.error(e);
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
            saveBtn.innerHTML = '<span class="spinner" style="width:12px;height:12px;display:inline-block"></span><strong>CONFLICT (Version {v})</strong>: Data changed elsewhere.')).replace('{v}', state.serverVersion);
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
            toggleBatchEdit(false);
            return;
        }
        
        const saveBtn = document.getElementById('editor-batch-save-btn');
        const originalText = saveBtn.innerHTML;
        saveBtn.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> ' + window.ATM.i18n.t('editor.saving', 'Saving...');
        saveBtn.disabled = true;
        
        try {
            const res = await window.ATM.api.post(`games/${encodeURIComponent(currentGameId)}/translations/batch-update`, {
                items: itemsToUpdate
            });
            
            if (res.status === 'success') {
                if (window.ATM.events) {
                    window.ATM.events.publish('');
                }
                drafts = {}; // Clear drafts for this game on batch save
                saveDrafts();
                toggleBatchEdit(false);
                fetchData(); 
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
            
            const finding = qaFindings[entry.id];
            if (finding) {
                if (finding.severity === 'error') {
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
                if (!isBatchEditing) {
                    actions.style.display = 'flex';
                } else {
                    actions.style.display = 'none';
                }
                input.style.borderColor = 'var(--warning)';
            } else {
                actions.style.display = 'none';
            }
            
            actions.style.justifyContent = 'flex-end';
            actions.style.gap = '8px';
            
            const cancelBtn = document.createElement('button');
            cancelBtn.className = 'btn-secondary heartbeat-neon-red';
            cancelBtn.innerHTML = '';
            
            const retryBtn = document.createElement('button');
            retryBtn.className = 'btn-secondary heartbeat-neon-orange';
            retryBtn.style.display = 'none';
            retryBtn.innerHTML = '';
            
            const saveBtn = document.createElement('button');
            saveBtn.className = 'btn-primary heartbeat-neon-green';
            saveBtn.innerHTML = 'Save';
            
            actions.appendChild(cancelBtn);
            actions.appendChild(retryBtn);
            actions.appendChild(saveBtn);
            
            const validationBox = document.createElement('div');
            validationBox.style.fontSize = '12px';
            validationBox.style.color = 'var(--danger)';
            validationBox.style.display = 'none';
            validationBox.style.marginTop = '-4px';
            
            input.addEventListener('focus', () => {
                if (!isBatchEditing) {
                    actions.style.display = 'flex';
                }
            });
            
            input.addEventListener('input', () => {
                updateDraft(entry.id, input.value, entry.translated);
                if (isBatchEditing) {
                    updateBatchSaveButtonText();
                }
                
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
                if (!isBatchEditing) {
                    if (input.value === entry.translated && !conflictStates[entry.id]) {
                        actions.style.display = 'none';
                        validationBox.style.display = 'none';
                        input.style.borderColor = 'var(--border-color)';
                    }
                }
            });
            
            input.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 'Enter') {
                    if (isBatchEditing) saveBatchEdits();
                    else saveRow(entry, input, row, actions, retryBtn, saveBtn, cancelBtn);
                } else if (e.key === 'Escape') {
                    if (conflictStates[entry.id]) return;
                    
                    input.value = entry.translated;
                    updateDraft(entry.id, input.value, entry.translated);
                    validationBox.style.display = 'none';
                    input.style.borderColor = 'var(--border-color)';
                    if (!isBatchEditing) actions.style.display = 'none';
                    if (isBatchEditing) updateBatchSaveButtonText();
                }
            });
            
            cancelBtn.addEventListener('click', () => {
                input.value = entry.translated;
                updateDraft(entry.id, input.value, entry.translated);
                
                if (!isBatchEditing) {
                    actions.style.display = 'none';
                }
                if (isBatchEditing) {
                    updateBatchSaveButtonText();
                }
                
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

            targetCol.appendChild(input);
            targetCol.appendChild(validationBox);
            targetCol.appendChild(actions);

            if (finding) {
                const qaBox = document.createElement('div');
                qaBox.className = 'qa-box';
                qaBox.style.fontSize = '12px';
                qaBox.style.padding = '6px';
                qaBox.style.borderRadius = '4px';
                qaBox.style.display = 'flex';
                qaBox.style.flexDirection = 'column';
                qaBox.style.gap = '4px';
                
                if (finding.severity === 'error') {
                    qaBox.style.background = 'rgba(239, 68, 68, 0.1)';
                    qaBox.style.color = 'var(--danger)';
                } else {
                    qaBox.style.background = 'rgba(245, 158, 11, 0.1)';
                    qaBox.style.color = 'var(--warning)';
                }

                const msgSpan = document.createElement('div');
                const strong = document.createElement('strong');
                strong.textContent = `QA ${finding.severity.toUpperCase()}`;
                msgSpan.appendChild(strong);
                msgSpan.appendChild(document.createTextNode(`: ${finding.message} `));
                qaBox.appendChild(msgSpan);
                targetCol.appendChild(qaBox);
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
