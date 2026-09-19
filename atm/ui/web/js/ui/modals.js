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
        confirm: (message, options = {}) => {
            return new Promise((resolve) => {
                const modal = document.getElementById('confirm-modal');
                const msgEl = document.getElementById('confirm-message');
                const btnYes = document.getElementById('confirm-yes');
                const btnNo = document.getElementById('confirm-no');
                
                // Checkbox elements
                const cbContainer = document.getElementById('confirm-checkbox-container');
                const cbInput = document.getElementById('confirm-checkbox');
                const cbLabel = document.getElementById('confirm-checkbox-label');
                
                if (!modal || !msgEl || !btnYes || !btnNo) {
                    console.error("Missing confirm modal elements:", {modal, msgEl, btnYes, btnNo});
                    if (options.checkboxLabel) resolve({ agreed: false, checked: false });
                    else resolve(false);
                    return;
                }
                
                msgEl.textContent = message;
                
                if (options.checkboxLabel && cbContainer && cbInput && cbLabel) {
                    cbLabel.textContent = options.checkboxLabel;
                    cbInput.checked = false;
                    cbContainer.style.display = 'block';
                } else if (cbContainer) {
                    cbContainer.style.display = 'none';
                }
                
                const cleanup = () => {
                    btnYes.removeEventListener('click', onYes);
                    btnNo.removeEventListener('click', onNo);
                    window.ATM.Modals.close('confirm-modal');
                };
                
                const onYes = () => {
                    cleanup();
                    if (options.checkboxLabel && cbInput) {
                        resolve({ agreed: true, checked: cbInput.checked });
                    } else {
                        resolve(true);
                    }
                };
                const onNo = () => {
                    cleanup();
                    if (options.checkboxLabel) {
                        resolve({ agreed: false, checked: false });
                    } else {
                        resolve(false);
                    }
                };
                
                btnYes.addEventListener('click', onYes);
                btnNo.addEventListener('click', onNo);
                
                window.ATM.Modals.open('confirm-modal');
            });
        },
        confirmSave: (message) => {
            return new Promise((resolve) => {
                const modal = document.getElementById('save-confirm-modal');
                const msgEl = document.getElementById('save-confirm-message');
                const btnSave = document.getElementById('save-confirm-save');
                const btnDiscard = document.getElementById('save-confirm-discard');
                const btnCancel = document.getElementById('save-confirm-cancel');
                
                if (!modal || !msgEl || !btnSave || !btnDiscard || !btnCancel) {
                    resolve('cancel');
                    return;
                }
                
                if (message) msgEl.textContent = message;
                
                const cleanup = () => {
                    btnSave.removeEventListener('click', onSave);
                    btnDiscard.removeEventListener('click', onDiscard);
                    btnCancel.removeEventListener('click', onCancel);
                    window.ATM.Modals.close('save-confirm-modal');
                };
                
                const onSave = () => { cleanup(); resolve('save'); };
                const onDiscard = () => { cleanup(); resolve('discard'); };
                const onCancel = () => { cleanup(); resolve('cancel'); };
                
                btnSave.addEventListener('click', onSave);
                btnDiscard.addEventListener('click', onDiscard);
                btnCancel.addEventListener('click', onCancel);
                
                window.ATM.Modals.open('save-confirm-modal');
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

                titleEl.textContent = title || (window.ATM.i18n ? window.ATM.i18n.t('common.info') : '');
                msgEl.textContent = message;

                const cleanup = () => {
                    btnOk.removeEventListener('click', onOk);
                    window.ATM.Modals.close('info-modal');
                };
                const onOk = () => { cleanup(); resolve(); };

                btnOk.addEventListener('click', onOk);
                window.ATM.Modals.open('info-modal');
            });
        },
        prompt: (message, defaultValue) => {
            return new Promise((resolve) => {
                const modal = document.getElementById('prompt-modal');
                const msgEl = document.getElementById('prompt-message');
                const inputEl = document.getElementById('prompt-input');
                const btnYes = document.getElementById('prompt-yes');
                const btnNo = document.getElementById('prompt-no');

                if (!modal || !msgEl || !inputEl || !btnYes || !btnNo) {
                    const fallback = window.prompt(message, defaultValue);
                    resolve(fallback);
                    return;
                }

                msgEl.textContent = message;
                inputEl.value = defaultValue || '';

                const cleanup = () => {
                    btnYes.removeEventListener('click', onYes);
                    btnNo.removeEventListener('click', onNo);
                    window.ATM.Modals.close('prompt-modal');
                };
                
                const onYes = () => { cleanup(); resolve(inputEl.value); };
                const onNo = () => { cleanup(); resolve(null); };
                
                btnYes.addEventListener('click', onYes);
                btnNo.addEventListener('click', onNo);
                
                window.ATM.Modals.open('prompt-modal');
                setTimeout(() => inputEl.focus(), 50);
            });
        }
    };
})();

