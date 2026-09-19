window.ATM = window.ATM || {};

window.ATM.Glossary = (function() {
    let currentGameId = null;
    let searchDebounceTimer = null;
    let isSelectionMode = false;
    let selectedTerms = new Set();
    let cachedTerms = [];

    const t = (key, fallback = '') => {
        return (window.ATM.i18n ? window.ATM.i18n.t(key) : null) || fallback;
    };

    const updateSelectionControls = () => {
        const deleteBtn = document.getElementById('glossary-delete-selected-btn');
        if (deleteBtn) {
            deleteBtn.textContent = t('glossary.btn_delete_selected', 'Xóa ({count})').replace('{count}', selectedTerms.size);
            deleteBtn.disabled = selectedTerms.size === 0;
        }

        const selectAllBtn = document.getElementById('glossary-select-all-btn');
        if (selectAllBtn) {
            const allSelected = cachedTerms.length > 0 && selectedTerms.size === cachedTerms.length;
            selectAllBtn.textContent = allSelected ? t('glossary.btn_deselect_all', 'Bỏ chọn tất cả') : t('glossary.btn_select_all', 'Chọn tất cả');
        }
    };

    const enterSelectionMode = () => {
        if (cachedTerms.length === 0) return;
        isSelectionMode = true;
        selectedTerms.clear();

        const btnMode = document.getElementById('glossary-select-mode-btn');
        const controls = document.getElementById('glossary-selection-controls');
        const btnImport = document.getElementById('glossary-import-btn');
        const btnExport = document.getElementById('glossary-export-btn');
        const listEl = document.getElementById('glossary-list');

        if (btnMode) btnMode.style.display = 'none';
        if (controls) controls.style.display = 'flex';
        if (btnImport) btnImport.style.display = 'none';
        if (btnExport) btnExport.style.display = 'none';

        if (listEl) {
            listEl.classList.add('selection-mode');
            listEl.querySelectorAll('.glossary-item-select-col').forEach(el => {
                el.style.display = 'flex';
                el.style.width = '24px';
                el.style.minWidth = '24px';
                el.style.opacity = '1';
            });
            listEl.querySelectorAll('.glossary-item').forEach(el => {
                el.classList.remove('is-selected');
                const cb = el.querySelector('.glossary-checkbox');
                if (cb) cb.checked = false;
            });
        }

        updateSelectionControls();
    };

    const exitSelectionMode = () => {
        isSelectionMode = false;
        selectedTerms.clear();

        const btnMode = document.getElementById('glossary-select-mode-btn');
        const controls = document.getElementById('glossary-selection-controls');
        const btnImport = document.getElementById('glossary-import-btn');
        const btnExport = document.getElementById('glossary-export-btn');
        const listEl = document.getElementById('glossary-list');

        if (btnMode) btnMode.style.display = cachedTerms.length > 0 ? 'inline-flex' : 'none';
        if (controls) controls.style.display = 'none';
        if (btnImport) btnImport.style.display = 'inline-flex';
        if (btnExport) btnExport.style.display = 'inline-flex';

        if (listEl) {
            listEl.classList.remove('selection-mode');
            listEl.querySelectorAll('.glossary-item-select-col').forEach(el => {
                el.style.display = 'none';
                el.style.width = '0';
                el.style.minWidth = '0';
                el.style.opacity = '0';
            });
            listEl.querySelectorAll('.glossary-item').forEach(el => {
                el.classList.remove('is-selected');
                const cb = el.querySelector('.glossary-checkbox');
                if (cb) cb.checked = false;
            });
        }
    };

    const toggleTermSelection = (termSource, rowEl) => {
        if (!rowEl) return;
        const cb = rowEl.querySelector('.glossary-checkbox');
        if (selectedTerms.has(termSource)) {
            selectedTerms.delete(termSource);
            rowEl.classList.remove('is-selected');
            if (cb) cb.checked = false;
        } else {
            selectedTerms.add(termSource);
            rowEl.classList.add('is-selected');
            if (cb) cb.checked = true;
        }
        updateSelectionControls();
    };

    const toggleSelectAll = () => {
        const listEl = document.getElementById('glossary-list');
        if (!listEl) return;
        const allSelected = cachedTerms.length > 0 && selectedTerms.size === cachedTerms.length;

        if (allSelected) {
            selectedTerms.clear();
            listEl.querySelectorAll('.glossary-item').forEach(el => {
                el.classList.remove('is-selected');
                const cb = el.querySelector('.glossary-checkbox');
                if (cb) cb.checked = false;
            });
        } else {
            cachedTerms.forEach(item => selectedTerms.add(item.source));
            listEl.querySelectorAll('.glossary-item').forEach(el => {
                el.classList.add('is-selected');
                const cb = el.querySelector('.glossary-checkbox');
                if (cb) cb.checked = true;
            });
        }
        updateSelectionControls();
    };

    const handleBatchDelete = async () => {
        if (selectedTerms.size === 0) {
            if (window.ATM.Toast) {
                window.ATM.Toast.show(t('glossary.no_term_selected', 'Chưa chọn thuật ngữ nào!'), 'warning');
            }
            return;
        }

        const count = selectedTerms.size;
        const msg = t('glossary.delete_multiple_confirm', 'Bạn có chắc chắn muốn xóa {count} thuật ngữ đã chọn?').replace('{count}', count);

        if (!window.ATM.Modals || !(await window.ATM.Modals.confirm(msg))) {
            return;
        }

        try {
            const res = await window.ATM.api.post('glossary/delete-multiple', {
                game_id: currentGameId,
                terms: Array.from(selectedTerms)
            });

            if (res.status === 'success') {
                const successMsg = t('glossary.delete_multiple_success', 'Đã xóa thành công {count} thuật ngữ.').replace('{count}', count);
                if (window.ATM.Toast) {
                    window.ATM.Toast.show(successMsg, 'success');
                }
                if (window.ATM.events) {
                    window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                }
                exitSelectionMode();
                loadList();
            } else {
                if (window.ATM.Toast) {
                    window.ATM.Toast.show(res.error || t('toast.delete_error', 'Lỗi khi xóa thuật ngữ'), 'error');
                }
            }
        } catch (err) {
            console.error('Failed to batch delete terms:', err);
            if (window.ATM.Toast) {
                window.ATM.Toast.show(t('toast.delete_error', 'Lỗi khi xóa thuật ngữ'), 'error');
            }
        }
    };

    const loadList = async () => {
        const listEl = document.getElementById('glossary-list');
        if (!listEl) return;

        try {
            const res = await window.ATM.api.get(`glossary/export?game_id=${currentGameId}&format=json`);
            listEl.replaceChildren();

            if (res.status === 'success' && res.data) {
                const data = JSON.parse(res.data);
                cachedTerms = data;

                const btnMode = document.getElementById('glossary-select-mode-btn');

                if (data.length === 0) {
                    const emptyDiv = document.createElement('div');
                    emptyDiv.style.textAlign = 'center';
                    emptyDiv.style.padding = '24px 12px';
                    emptyDiv.style.color = 'var(--text-muted)';
                    emptyDiv.textContent = t('glossary.empty', 'Chưa có thuật ngữ nào');
                    listEl.appendChild(emptyDiv);

                    if (btnMode) btnMode.style.display = 'none';
                    if (isSelectionMode) exitSelectionMode();
                    return;
                }

                if (btnMode && !isSelectionMode) {
                    btnMode.style.display = 'inline-flex';
                }

                data.forEach(item => {
                    const row = document.createElement('div');
                    row.className = 'glossary-item';
                    row.dataset.term = item.source;
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.style.justifyContent = 'space-between';
                    row.style.padding = '8px 12px';
                    row.style.borderRadius = 'var(--radius-sm, 6px)';
                    row.style.background = 'var(--bg-card)';
                    row.style.border = '1px solid var(--border-color)';
                    row.style.marginBottom = '6px';
                    row.style.transition = 'all 0.2s ease';

                    // Selection column with Checkbox
                    const selectCol = document.createElement('div');
                    selectCol.className = 'glossary-item-select-col';
                    selectCol.style.display = isSelectionMode ? 'flex' : 'none';
                    selectCol.style.width = isSelectionMode ? '24px' : '0';
                    selectCol.style.minWidth = isSelectionMode ? '24px' : '0';
                    selectCol.style.opacity = isSelectionMode ? '1' : '0';

                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'glossary-checkbox';
                    checkbox.checked = selectedTerms.has(item.source);
                    selectCol.appendChild(checkbox);

                    if (isSelectionMode && selectedTerms.has(item.source)) {
                        row.classList.add('is-selected');
                    }

                    // Text Content
                    const textSpan = document.createElement('span');
                    textSpan.style.color = 'var(--text-primary)';
                    textSpan.style.display = 'flex';
                    textSpan.style.alignItems = 'center';
                    textSpan.style.flex = '1';
                    textSpan.style.overflow = 'hidden';
                    textSpan.style.textOverflow = 'ellipsis';

                    const srcSpan = document.createElement('span');
                    srcSpan.style.fontWeight = '500';
                    srcSpan.textContent = item.source;

                    const arrowSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    arrowSvg.setAttribute('style', 'margin: 0 10px; color: var(--text-muted); flex-shrink: 0;');
                    arrowSvg.setAttribute('width', '14');
                    arrowSvg.setAttribute('height', '14');
                    arrowSvg.setAttribute('viewBox', '0 0 24 24');
                    arrowSvg.setAttribute('fill', 'none');
                    arrowSvg.setAttribute('stroke', 'currentColor');
                    arrowSvg.setAttribute('stroke-width', '2');
                    arrowSvg.innerHTML = '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>';

                    const tgtSpan = document.createElement('span');
                    tgtSpan.style.color = 'var(--accent)';
                    tgtSpan.textContent = item.target;

                    textSpan.appendChild(srcSpan);
                    textSpan.appendChild(arrowSvg);
                    textSpan.appendChild(tgtSpan);

                    // Delete button for single term
                    const delBtn = document.createElement('button');
                    delBtn.className = 'btn-icon btn-delete';
                    delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>';
                    delBtn.title = t('common.delete', 'Xóa');

                    delBtn.onclick = async (e) => {
                        e.stopPropagation();
                        const msg = (t('confirm.delete_glossary', 'Delete term: {word}?')).replace('{word}', item.source);
                        const confirmed = await window.ATM.Modals.confirm(msg);
                        if (confirmed) {
                            const delRes = await window.ATM.api.post('glossary/delete', {
                                game_id: currentGameId,
                                term: item.source
                            });
                            if (delRes.status === 'success') {
                                loadList();
                                if (window.ATM.events) {
                                    window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                                }
                            } else {
                                window.ATM.Toast.show(t('toast.delete_error', 'Lỗi khi xóa thuật ngữ'), 'error');
                            }
                        }
                    };

                    row.appendChild(selectCol);
                    row.appendChild(textSpan);
                    row.appendChild(delBtn);

                    // Row click in selection mode
                    row.onclick = () => {
                        if (isSelectionMode) {
                            toggleTermSelection(item.source, row);
                        }
                    };

                    listEl.appendChild(row);
                });

                if (isSelectionMode) {
                    listEl.classList.add('selection-mode');
                    updateSelectionControls();
                }
            }
        } catch (e) {
            console.error('Failed to load glossary list', e);
        }
    };

    const init = () => {
        document.body.addEventListener('click', async (e) => {
            // Close buttons
            if (e.target.closest('#glossary-modal-close-btn') || 
                e.target.closest('#glossary-close-btn') || 
                e.target.closest('#glossary-save-btn')) {
                if (window.ATM.Modals) window.ATM.Modals.close('glossary-modal');
            }
            
            // Selection mode toggle
            if (e.target.closest('#glossary-select-mode-btn')) {
                enterSelectionMode();
            }

            // Select All toggle
            if (e.target.closest('#glossary-select-all-btn')) {
                toggleSelectAll();
            }

            // Batch Delete
            if (e.target.closest('#glossary-delete-selected-btn')) {
                handleBatchDelete();
            }

            // Cancel Selection
            if (e.target.closest('#glossary-cancel-select-btn')) {
                exitSelectionMode();
            }

            // Import
            if (e.target.closest('#glossary-import-btn')) {
                const fileInput = document.getElementById('glossary-import-file');
                if (fileInput) fileInput.click();
            }
            
            // Add
            if (e.target.closest('#glossary-add-btn')) {
                const srcInput = document.getElementById('glossary-source');
                const tgtInput = document.getElementById('glossary-target');
                if (!srcInput || !tgtInput) return;
                const src = srcInput.value.trim();
                const tgt = tgtInput.value.trim();
                if (!src || !tgt) return;
                
                try {
                    const res = await window.ATM.api.post('glossary/apply', {
                        game_id: currentGameId,
                        parsed_data: [{source: src, target: tgt}],
                        strategy: 'merge'
                    });
                    if (res.status === 'success') {
                        if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.add_success', 'Đã thêm thuật ngữ thành công'), "success");
                        srcInput.value = '';
                        tgtInput.value = '';
                        loadList();
                        if (window.ATM.events) {
                            window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                        }
                    }
                } catch(err) {
                    if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.add_error', 'Lỗi khi thêm thuật ngữ'), "error");
                }
            }

            // Export
            if (e.target.closest('#glossary-export-btn')) {
                try {
                    const res = await window.ATM.api.get(`glossary/export?game_id=${currentGameId}&format=csv`);
                    if (res.status === 'success') {
                        const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `glossary_${currentGameId}.csv`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.export_success', 'Đã xuất file CSV'), "success");
                    }
                } catch(err) {
                    console.error(err);
                    if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.export_error', 'Lỗi xuất file'), "error");
                }
            }
        });

        let searchCtrl = null;
        document.body.addEventListener('input', (e) => {
            if (e.target && e.target.id === 'glossary-source') {
                const datalist = document.getElementById('glossary-suggestions');
                if (!datalist) return;
                const val = e.target.value.trim();
                if (val.length < 2) {
                    datalist.replaceChildren();
                    return;
                }
                
                if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(async () => {
                    if (searchCtrl) searchCtrl.abort();
                    searchCtrl = new AbortController();
                    try {
                        const res = await window.ATM.api.get(`cache/search?q=${encodeURIComponent(val)}&limit=10&page=1`, { signal: searchCtrl.signal });
                        if (res.status === 'success' && res.data && res.data.items) {
                            datalist.replaceChildren();
                            res.data.items.forEach(item => {
                                const option = document.createElement('option');
                                option.value = item.original;
                                datalist.appendChild(option);
                            });
                        }
                    } catch (err) {
                        if (err.name !== 'AbortError') console.error(err);
                    }
                }, 300);
            }
        });
        
        document.body.addEventListener('change', async (e) => {
            if (e.target && e.target.id === 'glossary-import-file') {
                const fileInput = e.target;
                const file = fileInput.files ? fileInput.files[0] : null;
                if (!file) return;
                
                const reader = new FileReader();
                reader.onload = async (ev) => {
                    const buffer = ev.target.result;
                    let content = '';
                    try {
                        const utf8Decoder = new TextDecoder('utf-8', { fatal: true });
                        content = utf8Decoder.decode(buffer);
                    } catch (_) {
                        // Fallback for Windows-1252 (ANSI) or Excel CSV
                        const ansiDecoder = new TextDecoder('windows-1252', { fatal: false });
                        content = ansiDecoder.decode(buffer);
                    }

                    // Strip UTF-8 BOM if present
                    if (content.charCodeAt(0) === 0xFEFF) {
                        content = content.slice(1);
                    }

                    try {
                        const res = await window.ATM.api.post('glossary/preview', {
                            game_id: currentGameId,
                            content: content,
                            format: 'csv'
                        });
                        
                        if (res.status === 'success') {
                            const data = res.data;
                            const msg = t('glossary.import_confirm', 'Confirm import?')
                                .replace('{new}', data.new ? data.new.length : 0)
                                .replace('{conflict}', data.conflict ? data.conflict.length : 0)
                                .replace('{duplicate}', data.duplicate ? data.duplicate.length : 0)
                                .replace('{invalid}', data.invalid ? data.invalid.length : 0);
                            
                            if (window.ATM.Modals && await window.ATM.Modals.confirm(msg)) {
                                const parsedData = [...(data.new || []), ...(data.conflict || []), ...(data.duplicate || [])];
                                const applyRes = await window.ATM.api.post('glossary/apply', {
                                    game_id: currentGameId,
                                    parsed_data: parsedData,
                                    strategy: 'merge'
                                });
                                if (applyRes.status === 'success') {
                                    if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.import_success', 'Import successful'), "success");
                                    loadList();
                                    if (window.ATM.events && parsedData.length > 0) {
                                        window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                                    }
                                } else {
                                    if (window.ATM.Toast) window.ATM.Toast.show(t('toast.server_error', 'Server error'), "error");
                                }
                            }
                        } else {
                            if (window.ATM.Toast) window.ATM.Toast.show(res.error || t('glossary.import_error', 'Import error'), "error");
                        }
                    } catch(err) {
                        console.error(err);
                        if (window.ATM.Toast) window.ATM.Toast.show(t('glossary.import_error', 'Import error'), "error");
                    } finally {
                        fileInput.value = ''; // reset
                    }
                };
                reader.readAsArrayBuffer(file);
            }
        });
    };

    const open = (gameId) => {
        currentGameId = gameId;
        if (window.ATM.Modals) window.ATM.Modals.open('glossary-modal');
        loadList();
    };

    const mount = (gameId) => {
        currentGameId = gameId;
        loadList();
    };

    return { init, open, mount, loadList };
})();


