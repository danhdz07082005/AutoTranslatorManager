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
                    textSpan.textContent = `${item.source} ➔ ${item.target}`;
                    textSpan.style.color = 'var(--text-primary)';
                    
                    const delBtn = document.createElement('button');
                    delBtn.innerHTML = '✖';
                    delBtn.className = 'btn btn-icon';
                    delBtn.style.color = '#fff';
                    delBtn.style.background = 'var(--danger-color, #ef4444)';
                    delBtn.style.padding = '2px 6px';
                    delBtn.style.borderRadius = '4px';
                    delBtn.style.fontSize = '12px';
                    delBtn.style.border = 'none';
                    delBtn.style.cursor = 'pointer';
                    delBtn.title = window.ATM.i18n.t('btn.delete') || 'Xóa';
                    delBtn.onclick = async () => {
                        const msg = (window.ATM.i18n.t('confirm.delete_glossary') || 'Xóa từ: {word}?').replace('{word}', item.source);
                        const confirmed = await window.ATM.Modals.confirm(msg);
                        if (confirmed) {
                            const res = await window.ATM.api.post('glossary/delete', {
                                game_id: currentGameId,
                                term: item.source
                            });
                            if (res.status === 'success') {
                                loadList();
                            } else {
                                window.ATM.Toast.show(window.ATM.i18n.t('toast.delete_error') || "Lỗi khi xóa từ", "error");
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
                        window.ATM.Toast.show("Đã thêm từ", "success");
                        srcInput.value = '';
                        tgtInput.value = '';
                        loadList();
                    }
                } catch(err) {
                    window.ATM.Toast.show("Lỗi thêm từ", "error");
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
                        if (window.ATM.Toast) window.ATM.Toast.show("Đã tải xuống file CSV", "success");
                    }
                } catch(err) {
                    console.error(err);
                    if (window.ATM.Toast) window.ATM.Toast.show("Lỗi khi xuất Glossary", "error");
                }
            }
        });

        if (sourceInput && datalist) {
            sourceInput.addEventListener('input', (e) => {
                const val = e.target.value.trim();
                if (val.length < 2) {
                    datalist.replaceChildren();
                    return;
                }
                
                if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
                searchDebounceTimer = setTimeout(async () => {
                    try {
                        const res = await window.ATM.api.get(`cache/search?q=${encodeURIComponent(val)}&limit=10&page=1`);
                        if (res.status === 'success' && res.data && res.data.items) {
                            datalist.replaceChildren();
                            res.data.items.forEach(item => {
                                const option = document.createElement('option');
                                option.value = item.original;
                                datalist.appendChild(option);
                            });
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }, 300);
            });
        }
        
        if (fileInput) {
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
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
                            const msg = `Preview Import: \n- ${data.new.length} New\n- ${data.conflict.length} Conflicts\n- ${data.duplicate.length} Duplicates\n- ${data.invalid.length} Invalid.\n\nBạn có muốn Merge (Ghi đè) không?`;
                            
                            if (await window.ATM.Modals.confirm(msg)) {
                                const parsedData = [...data.new, ...data.conflict, ...data.duplicate];
                                const applyRes = await window.ATM.api.post('glossary/apply', {
                                    game_id: currentGameId,
                                    parsed_data: parsedData,
                                    strategy: 'merge'
                                });
                                if (applyRes.status === 'success') {
                                    window.ATM.Toast.show("Đã import Glossary thành công", "success");
                                    loadList();
                                } else {
                                    window.ATM.Toast.show("Lỗi khi apply Glossary", "error");
                                }
                            }
                        }
                    } catch(err) {
                        console.error(err);
                        window.ATM.Toast.show("Lỗi Import", "error");
                    } finally {
                        fileInput.value = ''; // reset
                    }
                };
                reader.readAsText(file);
            });
        }
    };

    const open = (gameId) => {
        currentGameId = gameId;
        window.ATM.Modals.open('glossary-modal');
        loadList();
    };

    return { init, open };
})();

