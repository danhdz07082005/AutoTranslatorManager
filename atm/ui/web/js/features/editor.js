window.ATM = window.ATM || {};

window.ATM.Editor = (function() {
    let currentGameId = null;
    let currentPage = 1;
    let currentLimit = 50;
    let currentQuery = "";
    let currentFilter = "all";
    let entries = [];
    let qaFindings = {}; // { originalText: finding }

    let searchDebounceTimer;
    let fetchController = null;

    const init = () => {
        // Event delegation on the workspace container since the editor is mounted dynamically
        const container = document.getElementById('workspace-container');
        if (!container) return;
        
        container.addEventListener('click', (e) => {
            if (e.target.closest('#editor-search-btn') || e.target.closest('#editor-run-qa-btn')) {
                runQA();
            } else if (e.target.closest('#editor-prev-page')) {
                if (currentPage > 1) {
                    currentPage--;
                    fetchData();
                }
            } else if (e.target.closest('#editor-next-page')) {
                currentPage++;
                fetchData();
            }
        });

        container.addEventListener('input', (e) => {
            if (e.target.id === 'editor-search') {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(() => {
                    currentQuery = e.target.value.trim();
                    currentPage = 1;
                    fetchData();
                }, 300); // 300ms debounce
            }
        });

        container.addEventListener('change', (e) => {
            if (e.target.id === 'editor-filter-type') {
                currentFilter = e.target.value;
                renderList();
            }
        });
    };

    const open = (gameId) => {
        currentGameId = gameId;
        currentPage = 1;
        currentQuery = "";
        currentFilter = "all";
        qaFindings = {};
        
        const searchInput = document.getElementById('editor-search');
        if (searchInput) searchInput.value = "";
        
        fetchData();
    };

    const fetchData = async () => {
        if (fetchController) {
            fetchController.abort(); // Cancel stale request
        }
        fetchController = new AbortController();

        try {
            const listEl = document.getElementById('editor-list');
            if (!listEl) return;
            
            while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
            const loadingDiv = document.createElement('div');
            loadingDiv.style.textAlign = 'center';
            loadingDiv.style.padding = '20px';
            loadingDiv.style.color = 'var(--text-muted)';
            loadingDiv.textContent = window.ATM.i18n ? window.ATM.i18n.t('editor.loading') || 'Loading...' : 'Loading...';
            listEl.appendChild(loadingDiv);
            
            const res = await window.ATM.api.get(`cache/search?q=${encodeURIComponent(currentQuery)}&page=${currentPage}&limit=${currentLimit}`, {
                signal: fetchController.signal
            });
            
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
                
                // Reset QA when fetching new page
                qaFindings = {};
                renderList();
            }
        } catch (e) {
            if (e.name !== 'NetworkError' && e.name !== 'AbortError') {
                console.error(e);
                if (window.ATM.Toast) window.ATM.Toast.show('Lỗi khi tải dữ liệu', true);
            }
        }
    };

    const runQA = async () => {
        if (entries.length === 0) return;
        const qaBtn = document.getElementById('editor-run-qa-btn');
        try {
            if (qaBtn) {
                qaBtn.textContent = window.ATM.i18n.t('editor.qa_running');
                qaBtn.disabled = true;
            }

            const payload = entries.map((e, idx) => ({
                id: idx.toString(),
                source: e.original,
                translated: e.translated
            }));

            const res = await window.ATM.api.post('cache/qa-review', { entries: payload });
            if (res.status === 'success') {
                qaFindings = {};
                for (const [idxStr, findings] of Object.entries(res.data)) {
                    const idx = parseInt(idxStr);
                    if (findings && findings.length > 0) {
                        qaFindings[entries[idx].original] = findings[0]; // Just take first finding for simplicity
                    }
                }
                
                const filterSel = document.getElementById('editor-filter-type');
                if (Object.keys(qaFindings).length > 0) {
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('editor.qa_found', {count: Object.keys(qaFindings).length}), 'warning');
                    if (filterSel && filterSel.value !== 'qa_error') {
                        filterSel.value = 'qa_error';
                        currentFilter = 'qa_error';
                    }
                } else {
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('editor.qa_clean'), 'success');
                }
                renderList();
            }
        } catch (e) {
            console.error(e);
            if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('editor.qa_error'), 'error');
        } finally {
            if (qaBtn) {
                const btnText = window.ATM.i18n ? window.ATM.i18n.t('editor.run_qa') || 'Run QA Scanner' : 'Run QA Scanner';
                qaBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> ' + btnText;
                qaBtn.disabled = false;
            }
        }
    };

    const handleSuggestAccept = async (original, newTranslated) => {
        try {
            await window.ATM.api.post('cache/update', {
                game_id: currentGameId,
                key: original,
                value: newTranslated
            });
            window.ATM.Toast.show(window.ATM.i18n.t('editor.apply_success'), 'success');
            // Update local state and remove QA warning
            const entry = entries.find(e => e.original === original);
            if (entry) {
                entry.translated = newTranslated;
                delete qaFindings[original];
            }
            renderList();
        } catch (e) {
            window.ATM.Toast.show(window.ATM.i18n.t('editor.apply_error'), 'error');
        }
    };

    
    const updateQADomLocal = (original, finding) => {
        const safeId = 'row-' + btoa(encodeURIComponent(original)).replace(/[^a-zA-Z0-9]/g, '');
        const row = document.getElementById(safeId);
        if (!row) return; // if not rendered, do nothing
        
        // Remove existing QA boxes inside targetCol
        const targetCol = row.children[1];
        if (targetCol) {
            const existingQa = targetCol.querySelectorAll('.qa-box');
            existingQa.forEach(el => el.remove());
        }
        
        if (finding) {
            if (finding.severity === 'error') {
                row.style.borderColor = 'var(--danger)';
                row.style.boxShadow = '0 0 0 1px var(--danger)';
            } else {
                row.style.borderColor = 'var(--warning)';
                row.style.boxShadow = '0 0 0 1px var(--warning)';
            }
            
            // Re-render QA box (simplified for local patch)
            const qaBox = document.createElement('div');
                qaBox.className = 'qa-box';
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
            
            const badge = document.createElement('span');
            badge.className = 'badge';
            badge.textContent = finding.confidence;
            msgSpan.appendChild(badge);
            qaBox.appendChild(msgSpan);
            targetCol.appendChild(qaBox);
        } else {
            row.style.borderColor = 'var(--border-color)';
            row.style.boxShadow = 'none';
        }
    };

    const renderList = () => {
        const listEl = document.getElementById('editor-list');
        if (!listEl) return;  // Editor not mounted  silently skip
        while (listEl.firstChild) listEl.removeChild(listEl.firstChild);
        
        let displayEntries = entries;
        if (currentFilter === 'qa_error') {
            displayEntries = entries.filter(e => qaFindings[e.original]);
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
            const safeId = 'row-' + btoa(encodeURIComponent(entry.original)).replace(/[^a-zA-Z0-9]/g, '');
            row.id = safeId;
            row.style.display = 'flex';
            row.style.gap = '16px';
            row.style.padding = '8px';
            row.style.background = 'var(--bg-card)';
            row.style.borderRadius = '6px';
            row.style.border = '1px solid var(--border-color)';
            
            const finding = qaFindings[entry.original];
            if (finding) {
                if (finding.severity === 'error') {
                    row.style.borderColor = 'var(--danger)';
                    row.style.boxShadow = '0 0 0 1px var(--danger)';
                } else {
                    row.style.borderColor = 'var(--warning)';
                    row.style.boxShadow = '0 0 0 1px var(--warning)';
                }
            }

            // Source Col
            const sourceCol = document.createElement('div');
            sourceCol.style.flex = '1';
            sourceCol.style.fontSize = '13px';
            sourceCol.style.padding = '8px';
            sourceCol.style.background = 'var(--bg-base)';
            sourceCol.style.borderRadius = '4px';
            sourceCol.style.whiteSpace = 'pre-wrap';
            sourceCol.style.wordBreak = 'break-word';
            sourceCol.textContent = entry.original;
            
            // Target Col
            const targetCol = document.createElement('div');
            targetCol.style.flex = '1';
            targetCol.style.display = 'flex';
            targetCol.style.flexDirection = 'column';
            targetCol.style.gap = '8px';

            const input = document.createElement('textarea');
            input.value = entry.translated;
            input.className = 'themed-input';
            input.style.width = '100%';
            input.style.minHeight = '60px';
            input.style.padding = '8px';
            input.style.fontSize = '13px';
            input.style.resize = 'vertical';
            
            let debounceTimer;
            input.addEventListener('input', () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(async () => {
                    const newValue = input.value;
                    const oldValue = entry.translated;
                    if (newValue === oldValue) return;
                    
                    try {
                        await window.ATM.api.post('cache/update', {
                            game_id: currentGameId,
                            key: entry.original,
                            value: newValue
                        });
                        
                        entry.translated = newValue;
                        if (qaFindings[entry.original]) {
                            delete qaFindings[entry.original];
                            updateQADomLocal(entry.original, null);
                        }
                    } catch(e) {
                        console.error(e);
                        // Graceful Reversion
                        input.value = oldValue;
                        if (window.ATM.Toast) {
                            window.ATM.Toast.show(e.message || window.ATM.i18n.t('editor.save_error'), true);
                        }
                    }
                }, 1000);
            });

            targetCol.appendChild(input);

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
                
                const badge = document.createElement('span');
                badge.className = 'badge';
                badge.textContent = finding.confidence;
                msgSpan.appendChild(badge);
                
                qaBox.appendChild(msgSpan);

                if (finding.suggestion) {
                    const suggBox = document.createElement('div');
                    suggBox.style.display = 'flex';
                    suggBox.style.alignItems = 'center';
                    suggBox.style.gap = '8px';
                    suggBox.style.marginTop = '4px';
                    
                    const suggText = document.createElement('div');
                    suggText.style.flex = '1';
                    suggText.style.background = 'var(--bg-base)';
                    suggText.style.padding = '4px';
                    suggText.style.borderRadius = '2px';
                    suggText.textContent = finding.suggestion;

                    const accBtn = document.createElement('button');
                    accBtn.className = 'btn-primary';
                    accBtn.style.padding = '2px 8px';
                    accBtn.style.fontSize = '11px';
                    accBtn.textContent = window.ATM.i18n ? window.ATM.i18n.t('editor.accept') || 'Accept' : 'Accept';
                    accBtn.addEventListener('click', () => handleSuggestAccept(entry.original, finding.suggestion));

                    suggBox.appendChild(suggText);
                    suggBox.appendChild(accBtn);
                    qaBox.appendChild(suggBox);
                }

                targetCol.appendChild(qaBox);
            }

            row.appendChild(sourceCol);
            row.appendChild(targetCol);
            listEl.appendChild(row);
        });
    };

    const close = () => {
        if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
        currentGameId = null;
    };

    return { init, open, close };
})();

