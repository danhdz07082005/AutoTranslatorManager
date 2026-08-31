try { fetch('/api/ping?client_id=DEBUG_APP_JS_TOP'); } catch(e) {}
window.ATM = window.ATM || {};
window.ATM.state = window.ATM.state || {};
window.ATM.features = window.ATM.features || {};
window.ATM.ui = window.ATM.ui || {};
window.ATM.core = window.ATM.core || {};

let isInitialized = false;
function initWorkspace() {
    if (isInitialized) return;
    isInitialized = true;
    
    try { fetch('/api/ping?client_id=DEBUG_INIT_WORKSPACE'); } catch(e) {}
    console.log('[ATM Workspace] System Initializing...');
    
    const helloScreen = document.getElementById('hello-screen');
    const loadingBar = document.getElementById('hello-loading-bar');
    
    if (helloScreen && loadingBar) {
        let pct = 0;
        const interval = setInterval(() => {
            pct += (100 / 30);
            loadingBar.style.width = Math.min(pct, 100) + '%';
            if (pct >= 100) {
                clearInterval(interval);
                helloScreen.style.opacity = '0';
                helloScreen.style.transition = 'opacity 0.5s ease';
                setTimeout(() => helloScreen.style.display = 'none', 500);
            }
        }, 100);
    }
    
    // --- Nơi khởi tạo các module ---
    try {
        if (window.ATM.Theme) window.ATM.Theme.init();
        if (window.ATM.Modals) window.ATM.Modals.init();
        if (window.ATM.Games) window.ATM.Games.init();
        if (window.ATM.Settings) window.ATM.Settings.init();
        if (window.ATM.Data) window.ATM.Data.init();
        if (window.ATM.Glossary) window.ATM.Glossary.init();
        if (window.ATM.Editor) window.ATM.Editor.init();
        if (window.ATM.TM) window.ATM.TM.init();
    } catch (e) {
        console.error("Initialization Error: ", e);
    }
    
    // Tải dữ liệu ban đầu và dọn màn hình chờ khi thực sự xong
    Promise.all([
        window.ATM.Settings ? window.ATM.Settings.load() : Promise.resolve(),
        window.ATM.Data ? window.ATM.Data.refresh(true) : Promise.resolve()
    ]).catch(e => {
        console.error("Data Load Error: ", e);
    });
    
    // --- Shutdown Logic ---
    const exitBtn = document.getElementById('exit-btn');
    if (exitBtn) {
        exitBtn.addEventListener('click', async () => {
            const msg = window.ATM.i18n ? (window.ATM.i18n.t('confirm.exit') || 'Bạn có chắc chắn muốn thoát ứng dụng?') : 'Bạn có chắc chắn muốn thoát ứng dụng?';
            const confirmed = await window.ATM.Modals.confirm(msg);
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
    function sendHeartbeat() {
        if (window.ATM && window.ATM.api && window.ATM.api.get) {
            window.ATM.api.get(`ping?client_id=${clientId}`).catch(() => {
                console.warn('[ATM Heartbeat] Connection lost or Backend sleeping.');
            });
        }
    }
    sendHeartbeat();
    setInterval(sendHeartbeat, 5000);

    window.addEventListener('pagehide', () => {
        if (navigator.sendBeacon) {
            navigator.sendBeacon(`/api/ping/disconnect?client_id=${clientId}`);
        }
    });

    // --- Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-links li');
    const viewSections = document.querySelectorAll('.view-section');
    const sidebar = document.getElementById('sidebar');
    const sidebarPinSwitch = document.getElementById('sidebar-pin-switch');
    
    // Sidebar toggle (Pinned state)
    if (sidebarPinSwitch && sidebar) {
        // Load pinned state from settings
        const settings = window.ATM.store.get('atm_settings', {});
        if (settings.sidebar_pinned === true) {
            sidebar.classList.add('expanded');
            sidebarPinSwitch.checked = true;
        }
        
        sidebarPinSwitch.addEventListener('change', (e) => {
            sidebar.classList.toggle('expanded', e.target.checked);
            
            // Save state
            const currentSettings = window.ATM.store.get('atm_settings', {});
            currentSettings.sidebar_pinned = e.target.checked;
            localStorage.setItem('atm_settings', JSON.stringify(currentSettings));
        });
        
        const sidebarOverlay = document.getElementById('sidebar-overlay');
        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', () => {
                sidebar.classList.remove('expanded');
            });
        }
    }

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            const targetId = link.getAttribute('data-target');
            if (!targetId) return;
            
            if (targetId === 'library-view') window.ATM.navigation.showLibrary();
            else if (targetId === 'settings-view') window.ATM.navigation.showSettings();
            else if (targetId === 'marketplace-view') window.ATM.navigation.showMarketplace();
            else if (targetId === 'data-view') {
                window.ATM.navigation.showData();
                if (window.ATM.Data) window.ATM.Data.refresh(true);
            }
            
            // Close sidebar on mobile after clicking a link
            if (window.innerWidth <= 768 && sidebar) {
                sidebar.classList.remove('expanded');
            }
        });
    });

    // Hydrate Workspace State (Task 2.5)
    setTimeout(() => {
        const savedGameId = sessionStorage.getItem('atm_current_workspace');
        if (savedGameId && window.ATM.Workspace) {
            window.ATM.Workspace.open(savedGameId);
        }
    }, 200);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWorkspace);
} else {
    initWorkspace();
}




