window.ATM = window.ATM || {};

window.ATM.Settings = (function() {
    return {
        init: () => {
            const toggle = document.getElementById('theme-toggle');
            const deepl = document.getElementById('deepl-api-key');
            const tmEl = document.getElementById('tm-threshold');
            const langSel = document.getElementById('ui-lang-select');

            const saveSettings = () => {
                const isDark = toggle ? toggle.checked : true;
                window.ATM.api.post('settings', {
                    dark_mode: isDark,
                    deepl_api_key: deepl ? deepl.value : '',
                    translation_memory_threshold: tmEl ? Number(tmEl.value) : 0.85,
                    ui_language: langSel ? langSel.value : 'vi'
                }).then(() => {
                    if (langSel && langSel.value !== window.ATM.i18n.getLang()) {
                        window.ATM.i18n.setLang(langSel.value);
                    }
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.settings_saved') || 'Đã lưu cài đặt');
                }).catch(() => {
                    if (window.ATM.Toast) window.ATM.Toast.show(window.ATM.i18n.t('toast.settings_error') || 'Lỗi lưu cài đặt', true);
                });
            };

            if (deepl) deepl.addEventListener('change', saveSettings);
            if (tmEl) tmEl.addEventListener('change', saveSettings);
            if (langSel) langSel.addEventListener('change', saveSettings);
            // toggle 'theme-toggle' is handled in theme.js for saving, but we can also bind it here or let theme.js handle it.
            // Actually, theme.js ONLY saves dark_mode, so let's let theme.js do it.
            
            
            // Accent color picker
            const picker = document.getElementById('accent-color-picker');
            const resetBtn = document.getElementById('accent-reset-btn');
            
            const applyAccent = (hex) => {
                if (!hex) return;
                document.documentElement.style.setProperty('--accent', hex);
                const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
                if (m) {
                    const r = parseInt(m[1], 16), g = parseInt(m[2], 16), b = parseInt(m[3], 16);
                    document.documentElement.style.setProperty('--accent-rgb', `${r}, ${g}, ${b}`);
                }
                localStorage.setItem('atm_accent', hex);
            };

            if (picker) {
                picker.addEventListener('input', (e) => applyAccent(e.target.value));
            }
            if (resetBtn) {
                resetBtn.addEventListener('click', () => {
                    const DEFAULT_ACCENT = '#3b82f6';
                    if (picker) picker.value = DEFAULT_ACCENT;
                    applyAccent(DEFAULT_ACCENT);
                });
            }
        },
        
        load: async () => {
            try {
                const s = await window.ATM.api.get('settings');
                
                const toggle = document.getElementById('theme-toggle');
                if (toggle) {
                    toggle.checked = s.dark_mode !== false;
                    if (window.ATM.Theme && window.ATM.Theme.applyTheme) {
                        window.ATM.Theme.applyTheme(toggle.checked);
                    }
                    const localSettings = JSON.parse(localStorage.getItem('atm_settings') || '{}');
                    localSettings.dark_mode = toggle.checked;
                    localStorage.setItem('atm_settings', JSON.stringify(localSettings));
                }

                if (s.ui_language && s.ui_language !== window.ATM.i18n.getLang()) {
                    window.ATM.i18n.setLang(s.ui_language);
                }
                const langSel = document.getElementById('ui-lang-select');
                if (langSel) langSel.value = s.ui_language || 'vi';

                const deepl = document.getElementById('deepl-api-key');
                if (deepl) deepl.value = s.deepl_api_key || '';

                const tmEl = document.getElementById('tm-threshold');
                if (tmEl) tmEl.value = s.translation_memory_threshold != null ? s.translation_memory_threshold : 0.85;

                const savedAccent = localStorage.getItem('atm_accent');
                if (savedAccent) {
                    const picker = document.getElementById('accent-color-picker');
                    if (picker) picker.value = savedAccent;
                }
            } catch (e) {
                console.error('Failed to load settings:', e);
            }
        }
    };
})();
",



