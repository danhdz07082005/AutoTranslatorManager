window.ATM = window.ATM || {};

window.ATM.Theme = (function() {
    const applyTheme = (isDark, accentColor = null) => {
        document.documentElement.classList.toggle('theme-dark', isDark);
        if (accentColor) {
            document.documentElement.style.setProperty('--accent', accentColor);
        } else {
            document.documentElement.style.removeProperty('--accent');
        }
        const toggleInput = document.getElementById('theme-toggle');
        if (toggleInput) toggleInput.checked = isDark;
        
        const picker = document.getElementById('accent-color-picker');
        if (picker && accentColor) picker.value = accentColor;
    };

    return {
        applyTheme,
        init: () => {
            const settings = JSON.parse(localS
<truncated 92920 bytes>

NOTE: The output was truncated because it was too long. Use a more targeted query or a smaller range to get the information you need.