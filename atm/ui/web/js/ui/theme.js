window.ATM = window.ATM || {};

window.ATM.Theme = (function() {
    const applyTheme = (isDark) => {
        document.documentElement.classList.toggle('theme-dark', isDark);
        document.documentElement.style.backgroundColor = isDark ? '#0F172A' : '#F8F9FA';
        const toggleInput = document.getElementById('theme-toggle');
        if (toggleInput) toggleInput.checked = isDark;
    };

    return {
        applyTheme,
        init: () => {
            // Đồng bộ UI với trạng thái đã load từ <head>
            const settings = window.ATM.store.get('atm_settings', {});
            const isDark = (typeof serverDarkMode !== 'undefined') ? serverDarkMode : (settings.dark_mode !== false);
            applyTheme(isDark);

            // Gắn event listener cho toggle
            const toggleInput = document.getElementById('theme-toggle');
            if (toggleInput) {
                toggleInput.addEventListener('change', (e) => {
                    const darkEnabled = e.target.checked;
                    applyTheme(darkEnabled);
                    
                    // Cập nhật localStorage
                    const currentSettings = window.ATM.store.get('atm_settings', {});
                    currentSettings.dark_mode = darkEnabled;
                    window.ATM.store.set('atm_settings', currentSettings);
                    
                    // Sync với Backend (Non-blocking)
                    if (window.ATM.api) {
                        window.ATM.api.post('settings', { dark_mode: darkEnabled }, { keepalive: true }).catch(() => {});
                    }
                });
            }
        }
    };
})();
