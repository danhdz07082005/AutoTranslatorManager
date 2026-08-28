window.ATM = window.ATM || {};

window.ATM.Theme = (function() {
    const applyTheme = (isDark) => {
        document.documentElement.classList.toggle('theme-dark', isDark);
        const toggleInput = document.getElementById('theme-toggle');
        if (toggleInput) toggleInput.checked = isDark;
    };

    return {
        applyTheme,
        init: () => {
            // Đồng bộ UI với trạng thái đã load từ <head>
            const settings = window.ATM.store.get('atm_settings', {});
            const isDark = settings.dark_mode !== false; // Default là true
            applyTheme(isDark);

            // Gắn event listener cho toggle
            const toggleInput = document.getElementById('theme-toggle');
            if (toggleInput) {
                toggleInput.addEventListener('change', (e) => {
                    const darkEnabled = e.target.checked;
                    applyTheme(darkEnabled);
                    
                    // Cập nhật localStorage
                    settings.dark_mode = darkEnabled;
                    localStorage.setItem('atm_settings', JSON.stringify(settings));
                    
                    // Sync với Backend (Non-blocking)
                    if (window.ATM.api) {
                        window.ATM.api.post('settings', { dark_mode: darkEnabled }).catch(() => {});
                    }
                });
            }
        }
    };
})();
