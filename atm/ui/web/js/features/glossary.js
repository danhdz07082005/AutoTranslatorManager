window.ATM = window.ATM || {};

window.ATM.Glossary = (function() {
    let currentGameId = null;

    const init = () => {
        const importBtn = document.getElementById('glossary-import-btn');
        const exportBtn = document.getElementById('glossary-export-btn');
        const fileInput = document.getElementById('glossary-import-file');
        const closeBtn = document.getElementById('glossary-modal-close-btn');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                if (window.ATM.Modals) window.ATM.Modals.close('glossary-modal');
            });
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', async () => {
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
                } catch(e) {
                    console.error(e);
                    if (window.ATM.Toast) window.ATM.Toast.show("Lỗi khi xuất Glossary", "error");
                }
            });
        }

        if (importBtn && fileInput) {
            importBtn.addEventListener('click', () => fileInput.click());
            
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
                            const total = data.new.length + data.conflict.length + data.duplicate.length + data.invalid.length;
                            const msg = `Preview Import: \n- ${data.new.length} New\n- ${data.conflict.length} Conflicts\n- ${data.duplicate.length} Duplicates\n- ${data.invalid.length} Invalid.\n\nBạn có muốn Merge (Ghi đè) không?`;
                            
                            if (await window.ATM.Modals.confirm(msg)) {
                                // Extract valid entries for apply
                                const parsedData = [...data.new, ...data.conflict, ...data.duplicate]; // apply needs everything
                                const applyRes = await window.ATM.api.post('glossary/apply', {
                                    game_id: currentGameId,
                                    parsed_data: parsedData,
                                    strategy: 'merge'
                                });
                                if (applyRes.status === 'success') {
                                    window.ATM.Toast.show("Đã import Glossary thành công", "success");
                                    // Normally you'd reload the local UI list here
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
        // Currently, local rendering is handled loosely in index.html (there isn't an explicit load API endpoint for Glossary right now except via Editor). 
        // We assume Glossary modal has its manual add buttons mapped, but Phase 4 wants Import/Export.
    };

    return { init, open };
})();

