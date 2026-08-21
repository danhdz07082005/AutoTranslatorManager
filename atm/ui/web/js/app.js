window.ATM = window.ATM || {};
window.ATM.state = window.ATM.state || {};
window.ATM.features = window.ATM.features || {};
window.ATM.ui = window.ATM.ui || {};
window.ATM.core = window.ATM.core || {};

document.addEventListener('DOMContentLoaded', () => {
    console.log('[ATM Workspace] System Initializing...');
    
    // --- Nơi khởi tạo các module ---
    if (window.ATM.Theme) window.ATM.Theme.init();
    if (window.ATM.Modals) window.ATM.Modals.init();
    if (window.ATM.Games) window.ATM.Games.init();
    if (window.ATM.Settings) window.ATM.Settings.init();
    if (window.ATM.Data) window.ATM.Data.init();
    if (window.ATM.Editor) window.ATM.Editor.init();
    if (window.ATM.TM) window.ATM.TM.init();
    
    // Tải dữ liệu ban đầu
    setTimeout(() => {
        if (window.ATM.Settings) window.ATM.Settings.load();
        if (window.ATM.Data) window.ATM.Data.refresh(true);
    }, 100);
    
    // --- Hello Screen Logic (Loading 3 seconds) ---
    const helloScreen = document.getElementById('hello-screen');
    const loadingBar = document.getElementById('hello-loading-bar');
    if (helloScreen && loadingBar) {
        let pct = 0;
        const interval = setInterval(() => {
            pct += (100 / 30); // 3 seconds (30 * 100ms)
            loadingBar.style.width = Math.min(pct, 100) + '%';
            if (pct >= 100) {
                clearInterval(interval);
                helloScreen.style.opacity = '0';
                helloScreen.style.transition = 'opacity 0.5s ease';
                setTimeout(() => helloScreen.style.display = 'none', 500);
            }
        }, 100);
    }
    
    // --- Shutdown Logic ---
    const exitBtn = document.getElementById('exit-btn');
    if (exitBtn) {
        exitBtn.addEventListener('click', async () => {
            const msg = window.ATM.i18n ? (window.ATM.i18n.t('menu.exit_confirm') || 'Bạn có chắc chắn muốn thoát ứng dụng?') : 'Bạn có chắc chắn muốn thoát ứng dụng?';
            const confirmed = window.ATM.Modals ? await window.ATM.Modals.confirm(msg) : confirm(msg);
            if (confirmed) {
                const goodbye = document.getElementById('goodbye-screen');
                if (goodbye) goodbye.style.display = 'flex';
                
                // Đóng app sau 2 giây (Lưu ý: window.close chỉ chạy nếu script mở window đó)
                setTimeout(() => {
                    if (window.ATM.api) window.ATM.api.post('shutdown').catch(() => {});
                    window.close();
                }, 2000);
            }
        });
    }

    // --- Heartbeat System ---
    const clientId = 'c_' + Math.random().toString(36).substr(2, 9);
    setInterval(() => {
        if (ATM.api && ATM.api.get) {
            ATM.api.get(`ping?client_id=${clientId}`).catch(() => {
                console.warn('[ATM Heartbeat] Connection lost or Backend sleeping.');
            });
        }
    }, 5000);

    // --- Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-links li');
    const viewSections = document.querySelectorAll('.view-section');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            const targetId = link.getAttribute('data-target');
            viewSections.forEach(view => {
                if (view.id === targetId) {
                    view.classList.remove('hidden');
                    view.classList.add('active');
                    if (targetId === 'data-view' && window.ATM.Data) {
                        window.ATM.Data.refresh(true);
                    }
                } else {
                    view.classList.remove('active');
                    view.classList.add('hidden');
                }
            });
        });
    });
});

