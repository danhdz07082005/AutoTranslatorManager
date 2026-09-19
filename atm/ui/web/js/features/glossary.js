window.ATM = window.ATM || {};

window.ATM.Glossary = (function() {
    let currentGameId = null;
    let searchDebounceTimer = null;

    const loadList = async () => {
        const listEl = document.getElementById('glossary-list');
        if (!listEl) return;
        
        try {
            const res = await window.ATM.api.get(`glossary/export?game_id=${currentGameId}&format=json`);
            listEl.replaceChildren();
            if (res.status === 'success' && res.data) {
                const data = JSON.parse(res.data);
                data.forEach(item => {
                    const row = document.createElement('div');
                    row.style.display = 'flex';
                    row.style.justifyContent = 'space-between';
                    row.style.padding = '4px 8px';
                    row.style.borderBottom = '1px solid var(--border-color)';
                    
                    const textSpan = document.createElement('span');
                    textSpan.style.color = 'var(--text-primary)';
                    textSpan.style.display = 'flex';
                    textSpan.style.alignItems = 'center';
                    
                    const srcSpan = document.createElement('span');
                    srcSpan.textContent = item.source;
                    const tgtSpan = document.createElement('span');
                    tgtSpan.textContent = item.target;
                    
                    const arrowSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                    arrowSvg.setAttribute('style', 'margin: 0 10px; color: var(--text-muted);');
                    arrowSvg.setAttribute('width', '14');
                    arrowSvg.setAttribute('height', '14');
                    arrowSvg.setAttribute('viewBox', '0 0 24 24');
                    arrowSvg.setAttribute('fill', 'none');
                    arrowSvg.setAttribute('stroke', 'currentColor');
                    arrowSvg.setAttribute('stroke-width', '2');
                    arrowSvg.innerHTML = '<line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline>';
                    
                    textSpan.appendChild(srcSpan);
                    textSpan.appendChild(arrowSvg);
                    textSpan.appendChild(tgtSpan);
                    
                    const delBtn = document.createElement('button');
                    delBtn.className = 'btn-icon btn-delete';
                    delBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>';
                    delBtn.title = (window.ATM.i18n ? window.ATM.i18n.t('btn.delete') : null) || 'Delete';
                    delBtn.onclick = async () => {
                        const msg = (window.ATM.i18n.t('confirm.delete_glossary') || 'Delete term: {word}?').replace('{word}', item.source);
                        const confirmed = await window.ATM.Modals.confirm(msg);
                        if (confirmed) {
                            const res = await window.ATM.api.post('glossary/delete', {
                                game_id: currentGameId,
                                term: item.source
                            });
                            if (res.status === 'success') {
                                loadList();
                                if (window.ATM.events) {
                                    window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                                }
                            } else {
                                window.ATM.Toast.show(window.ATM.i18n.t('toast.delete_error') || "Error deleting term", "error");
                            }
                        }
                    };
                    
                    row.appendChild(textSpan);
                    row.appendChild(delBtn);
                    listEl.appendChild(row);
                });
            }
        } catch (e) {
            console.error("Failed to load glossary list", e);
        }
    };

    const init = () => {
        const fileInput = document.getElementById('glossary-import-file');
        const sourceInput = document.getElementById('glossary-source');
        const targetInput = document.getElementById('glossary-target');
        const datalist = document.getElementById('glossary-suggestions');

        document.body.addEventListener('click', async (e) => {
            // Close buttons
            if (e.target.closest('#glossary-modal-close-btn') || 
                e.target.closest('#glossary-close-btn') || 
                e.target.closest('#glossary-save-btn')) {
                if (window.ATM.Modals) window.ATM.Modals.close('glossary-modal');
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
                        window.ATM.Toast.show(window.ATM.i18n.t('glossary.add_success'), "success");
                        srcInput.value = '';
                        tgtInput.value = '';
                        loadList();
                        if (window.ATM.events) {
                            window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                        }
                    }
                } catch(err) {
                    window.ATM.Toast.show(window.ATM.i18n.t('glossary.add_error'), "error");
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
                        if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('glossary.export_success'), "success");
                    }
                } catch(err) {
                    console.error(err);
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('glossary.export_error'), "error");
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
                    const content = ev.target.result;
                    try {
                        const res = await window.ATM.api.post('glossary/preview', {
                            game_id: currentGameId,
                            content: content,
                            format: 'csv'
                        });
                        
                        if (res.status === 'success') {
                            const data = res.data;
                            const msg = window.ATM.i18n ? window.ATM.i18n.t('glossary.import_confirm', {
                                new: data.new ? data.new.length : 0,
                                conflict: data.conflict ? data.conflict.length : 0,
                                duplicate: data.duplicate ? data.duplicate.length : 0,
                                invalid: data.invalid ? data.invalid.length : 0
                            }) : 'Confirm import?';
                            
                            if (window.ATM.Modals && await window.ATM.Modals.confirm(msg)) {
                                const parsedData = [...(data.new || []), ...(data.conflict || []), ...(data.duplicate || [])];
                                const applyRes = await window.ATM.api.post('glossary/apply', {
                                    game_id: currentGameId,
                                    parsed_data: parsedData,
                                    strategy: 'merge'
                                });
                                if (applyRes.status === 'success') {
                                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('glossary.import_success') : "Import successful", "success");
                                    loadList();
                                    if (window.ATM.events && parsedData.length > 0) {
                                        window.ATM.events.publish('glossary:changed', { gameId: currentGameId });
                                    }
                                } else {
                                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('toast.server_error') : "Server error", "error");
                                }
                            }
                        }
                    } catch(err) {
                        console.error(err);
                        if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n ? window.ATM.i18n.t('glossary.import_error') : "Import error", "error");
                    } finally {
                        fileInput.value = ''; // reset
                    }
                };
                reader.readAsText(file);
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

