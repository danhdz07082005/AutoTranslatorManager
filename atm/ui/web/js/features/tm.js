window.ATM = window.ATM || {};

window.ATM.TM = (function() {
    return {
        init: () => {
            const closeBtn = document.getElementById('tm-modal-close-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    if (window.ATM.Modals) window.ATM.Modals.close('translation-memory-modal');
                });
            }
        },
        open: (gameId) => {
            console.log("Opening TM for", gameId);
        }
    };
})();

