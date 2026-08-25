window.ATM = window.ATM || {};

window.ATM.TM = (function() {
    let searchDebounceTimer = null;

    const performSearch = async (query) => {
        const suggContainer = document.getElementById('tm-suggestions');
        if (!suggContainer) return;
        
        if (!query || query.trim().length < 2) {
            suggContainer.replaceChildren();
            return;
        }

        try {
            const res = await window.ATM.api.get(`cache/search?q=${encodeURIComponent(query)}&limit=20&page=1`);
            suggContainer.replaceChildren();
            
            if (res.status === 'success' && res.data && res.data.items && res.data.items.length > 0) {
                res.data.items.forEach(item => {
                    const box = document.createElement('div');
                    box.style.background = 'var(--bg-hover)';
                    box.style.padding = '10px';
                    box.style.borderRadius = '8px';
                    box.style.borderLeft = '3px solid var(--accent)';
                    
                    const origP = document.createElement('p');
                    origP.textContent = item.original;
                    origP.style.margin = '0 0 4px 0';
                    origP.style.color = 'var(--text-secondary)';
                    origP.style.fontSize = '12px';
                    
                    const transP = document.createElement('p');
                    transP.textContent = item.translated;
                    transP.style.margin = '0';
                    transP.style.color = 'var(--text-primary)';
                    
                    box.appendChild(origP);
                    box.appendChild(transP);
                    suggContainer.appendChild(box);
                });
            } else {
                const noRes = document.createElement('p');
                noRes.textContent = "Không tìm thấy kết quả.";
                noRes.style.color = 'var(--text-muted)';
                suggContainer.appendChild(noRes);
            }
        } catch (e) {
            console.error("TM search error", e);
        }
    };

    return {
        init: () => {
            document.body.addEventListener('click', (e) => {
                if (e.target.closest('#tm-close-btn') || e.target.closest('#tm-modal-close-btn')) {
                    if (window.ATM.Modals) window.ATM.Modals.close('translation-memory-modal');
                }
                if (e.target.closest('#tm-find-btn')) {
                    const searchInput = document.getElementById('tm-source-text');
                    if (searchInput) performSearch(searchInput.value);
                }
            });

            const searchInput = document.getElementById('tm-source-text');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    const query = e.target.value;
                    if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
                    searchDebounceTimer = setTimeout(() => {
                        performSearch(query);
                    }, 400);
                });
            }
        },
        open: (gameId) => {
            const suggContainer = document.getElementById('tm-suggestions');
            if (suggContainer) suggContainer.replaceChildren();
            const searchInput = document.getElementById('tm-source-text');
            if (searchInput) searchInput.value = '';
        }
    };
})();

