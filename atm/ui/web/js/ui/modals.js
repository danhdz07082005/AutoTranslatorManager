window.ATM = window.ATM || {};

window.ATM.Modals = (function() {
    let activeModal = null;
    let previousFocus = null;

    const trapFocus = (e) => {
        if (!activeModal) return;
        const focusableEls = activeModal.querySelectorAll('a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])');
        if (focusableEls.length === 0) return;

        const firstEl = focusableEls[0];
        const lastEl = focusableEls[focusableEls.length - 1];

        if (e.key === 'Tab') {
            if (e.shiftKey) { // Shift + Tab
                if (document.activeElement === firstEl) {
                    lastEl.focus();
                    e.preventDefault();
                }
            } else { // Tab
                if (document.activeElement === lastEl) {
                    firstEl.focus();
                    e.preventDefault();
                }
            }
        }
    };

    const handleEscape = (e) => {
        if (e.key === 'Escape' && activeModal) {
            window.ATM.Modals.close(activeModal.id);
        }
    };

    return {
        init: () => {
            document.addEventListener('keydown', trapFocus);
            document.addEventListener('keydown', handleEscape);
            
            // Gán sự kiện đóng modal cho nút X hoặc vùng overlay
            document.querySelectorAll('.modal-overlay').forEach(overlay => {
                overlay.addEventListener('click', (e) => {
                    if (e.target === overlay) {
                        window.ATM.Modals.close(overlay.id);
                    }
                });
            });
            document.querySelectorAll('.btn-close').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const modal = btn.closest('.modal-overlay');
                    if (modal) window.ATM.Modals.close(modal.id);
                });
            });
        },
        open: (modalId) => {
            const modal = document.getElementById(modalId);
            if (!modal) return;
            previousFocus = document.activeElement; // Lưu lại phần tử đang focus
            activeModal = modal;
            modal.classList.remove('hidden');
            modal.style.display = 'flex'; // Hiện modal
            
            // Focus vào phần tử đầu tiên của modal
            const firstFocusable = modal.querySelector('button, input, textarea');
            if (firstFocusable) firstFocusable.focus();
        },
        close: (modalId) => {
            const modal = document.getElementById(modalId);
            if (!modal) return;
            modal.classList.add('hidden');
            modal.style.display = 'none'; // Ẩn modal
            activeModal = null;
            if (previousFocus) previousFocus.focus(); // Trả lại focus
        },
        confirm: (message) => {
            return new Promise((resolve) => {
                const modal = document.getElementById('confirm-modal');
                const msgEl = document.getElementById('confirm-message');
                const btnYes = document.getElementById('confirm-yes');
                const btnNo = document.getElementById('confirm-no');
                
                if (!modal || !msgEl || !btnYes || !btnNo) {
                    console.error("Missing confirm modal elements:", {modal, msgEl, btnYes, btnNo});
                    resolve(false);
                    return;
                }
                
                msgEl.textContent = message;
                
                const cleanup = () => {
                    btnYes.removeEventListener('click', onYes);
                    btnNo.removeEventListener('click', onNo);
                    window.ATM.Modals.close('confirm-modal');
                };
                
                const onYes = () => { cleanup(); resolve(true); };
                const onNo = () => { cleanup(); resolve(false); };
                
                btnYes.addEventListener('click', onYes);
                btnNo.addEventListener('click', onNo);
                
                window.ATM.Modals.open('confirm-modal');
            });
        },
        info: (title, message) => {
            return new Promise((resolve) => {
                const modal = document.getElementById('info-modal');
                const titleEl = document.getElementById('info-title');
                const msgEl = document.getElementById('info-message');
                const btnOk = document.getElementById('info-ok');

                if (!modal || !titleEl || !msgEl || !btnOk) {
                    console.error("Missing info modal elements");
                    resolve();
                    return;
                }

                titleEl.textContent = title || (window.ATM.i18n ? window.ATM.i18n.t('common.info') : 'Thông báo');
                msgEl.textContent = message;

                const cleanup = () => {
                    btnOk.removeEventListener('click', onOk);
                    window.ATM.Modals.close('info-modal');
                };
                const onOk = () => { cleanup(); resolve(); };

                btnOk.addEventListener('click', onOk);
                window.ATM.Modals.open('info-modal');
            });
        }
    };
})();

