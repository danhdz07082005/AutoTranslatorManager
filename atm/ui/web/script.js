/* =============================================
   ATM - Auto Translator Manager
   Frontend Logic (HTTP API Fetch)
   ============================================= */

let languages = {};

// --- Khởi tạo ---
document.addEventListener('DOMContentLoaded', () => {
    console.log('[ATM] Frontend ready. Loading data...');
    loadSettings();
    loadLanguages();
    loadGames();
    setupAddGameButton();
});

// --- Settings ---
async function loadSettings() {
    try {
        const settings = await apiGet('settings');
        document.getElementById('theme-toggle').checked = settings.dark_mode;
        document.getElementById('deepl-api-key').value = settings.deepl_api_key || '';
        document.body.classList.toggle('theme-light', !settings.dark_mode);
    } catch (e) {
        console.error('Failed to load settings:', e);
    }
}

async function saveSettings() {
    const isDark = document.getElementById('theme-toggle').checked;
    const apiKey = document.getElementById('deepl-api-key').value;
    
    document.body.classList.toggle('theme-light', !isDark);
    
    try {
        await apiPost('settings', { dark_mode: isDark, deepl_api_key: apiKey });
        showToast('⚙️ Đã lưu cấu hình');
    } catch (e) {
        showToast('Lỗi lưu cấu hình', true);
    }
}

// --- API Helpers ---
async function apiGet(endpoint) {
    const response = await fetch(`/api/${endpoint}`);
    if (!response.ok) throw new Error(response.statusText);
    return await response.json();
}

async function apiPost(endpoint, data = {}) {
    const response = await fetch(`/api/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!response.ok) throw new Error(response.statusText);
    return await response.json();
}

// --- Navigation ---
document.addEventListener('DOMContentLoaded', () => {
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
                } else {
                    view.classList.remove('active');
                    view.classList.add('hidden');
                }
            });
        });
    });
});

// --- Load Languages ---
async function loadLanguages() {
    try {
        languages = await apiGet('languages');
    } catch (e) {
        console.error('[ATM] Failed to load languages:', e);
        languages = {"auto": "Auto Detect", "ja": "Japanese", "vi": "Vietnamese", "en": "English"};
    }
}

function buildLangOptions(selectedValue, excludeAuto) {
    let html = '';
    for (const [code, name] of Object.entries(languages)) {
        if (excludeAuto && code === 'auto') continue;
        const selected = code === selectedValue ? 'selected' : '';
        html += `<option value="${code}" ${selected}>${name}</option>`;
    }
    return html;
}

// --- Add Game Button ---
function setupAddGameButton() {
    const btn = document.getElementById('add-game-btn');
    if (!btn) return;
    btn.addEventListener('click', async () => {
        btn.disabled = true;
        btn.innerHTML = '<span>⏳</span> Đang chọn...';
        try {
            const result = await apiPost('games/add');
            if (result && result.status === 'success') {
                showToast(`✅ Đã thêm: ${result.game.game_name}`);
                loadGames();
            } else if (result && result.error) {
                showToast(result.error, true);
            }
        } catch (e) {
            showToast('Lỗi khi thêm game: ' + e, true);
        }
        btn.disabled = false;
        btn.innerHTML = '<span>+</span> Add Game';
    });
}

// --- Load Games ---
async function loadGames() {
    const container = document.getElementById('games-container');
    if (!container) return;
    container.innerHTML = '';

    let games;
    try {
        games = await apiGet('games');
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><h3>Lỗi kết nối API</h3></div>';
        return;
    }

    if (!games || games.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                    <line x1="8" y1="21" x2="16" y2="21"></line>
                    <line x1="12" y1="17" x2="12" y2="21"></line>
                </svg>
                <h3>Chưa có game nào</h3>
                <p style="margin-top: 8px;">Bấm "+ Add Game" để bắt đầu.</p>
            </div>
        `;
        return;
    }

    games.forEach(game => {
        const card = document.createElement('div');
        card.className = 'game-card';
        card.id = `card-${game.id}`;

        const engineBadge = game.engine !== 'Unknown'
            ? `<span class="engine-badge">${game.engine}</span>`
            : '';

        card.innerHTML = `
            <div class="game-header">
                <div class="game-info">
                    <h3 title="${game.game_name}">${game.game_name}</h3>
                    <p class="game-path" title="${game.exe_path}">${game.exe_path}</p>
                </div>
                ${engineBadge}
            </div>
            <div class="lang-row">
                <div class="lang-group">
                    <label>Engine Dịch</label>
                    <select class="lang-select" data-game-id="${game.id}" data-lang-type="translator" onchange="onLangChange(this)">
                        <option value="google" ${game.translator === 'google' ? 'selected' : ''}>Google Translate</option>
                        <option value="deepl" ${game.translator === 'deepl' ? 'selected' : ''}>DeepL API (Pro)</option>
                    </select>
                </div>
                <div class="lang-group">
                    <label>Ngôn ngữ gốc</label>
                    <select class="lang-select" data-game-id="${game.id}" data-lang-type="input" onchange="onLangChange(this)">
                        ${buildLangOptions(game.input_lang, false)}
                    </select>
                </div>
                <span class="lang-arrow">→</span>
                <div class="lang-group">
                    <label>Dịch sang</label>
                    <select class="lang-select" data-game-id="${game.id}" data-lang-type="output" onchange="onLangChange(this)">
                        ${buildLangOptions(game.output_lang, true)}
                    </select>
                </div>
            </div>
            <div class="game-actions">
                <button class="btn-start" id="btn-start-${game.id}" onclick="startGame('${game.id}', this)">
                    ▶ Start Translation
                </button>
                <button class="btn-delete" onclick="deleteGame('${game.id}')" title="Xóa game">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    </svg>
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

// --- Language Change ---
async function onLangChange(selectEl) {
    const gameId = selectEl.dataset.gameId;
    const langType = selectEl.dataset.langType;
    const card = document.getElementById(`card-${gameId}`);
    if (!card) return;

    const inputSelect = card.querySelector('[data-lang-type="input"]');
    const outputSelect = card.querySelector('[data-lang-type="output"]');
    const transSelect = card.querySelector('[data-lang-type="translator"]');

    try {
        await apiPost('games/update-settings', {
            game_id: gameId,
            input_lang: inputSelect.value,
            output_lang: outputSelect.value,
            translator: transSelect ? transSelect.value : 'google'
        });
        showToast('🌐 Đã cập nhật ngôn ngữ');
    } catch (e) {
        showToast('Lỗi cập nhật ngôn ngữ', true);
    }
}

// --- Start / Stop Game ---
async function startGame(gameId, btnElement) {
    if (btnElement.classList.contains('running')) {
        // Stop
        btnElement.innerText = '⏳ Đang dừng...';
        try {
            await apiPost('games/stop', { game_id: gameId });
        } catch(e) {}
        btnElement.innerText = '▶ Start Translation';
        btnElement.classList.remove('running');
        showToast('⏹ Game đã dừng');
        return;
    }

    // Start
    btnElement.innerText = '⏳ Đang khởi tạo...';
    btnElement.classList.add('running');

    try {
        const result = await apiPost('games/start', { game_id: gameId });
        if (result.status === 'success') {
            showToast('🚀 Game đã khởi chạy! Bấm lại để dừng.');
            btnElement.innerText = '⏹ Stop Game';
        } else if (result.status === 'translating') {
            showToast('⏳ Đang tiến hành dịch offline...');
            btnElement.innerText = '0% Đang dịch...';
            btnElement.disabled = true; // Disable until done
            pollTranslationProgress(gameId, btnElement);
        } else {
            showToast('❌ ' + result.error, true);
            btnElement.innerText = '▶ Start Translation';
            btnElement.classList.remove('running');
        }
    } catch (e) {
        showToast('❌ Lỗi: ' + e, true);
        btnElement.innerText = '▶ Start Translation';
        btnElement.classList.remove('running');
    }
}

// --- Polling Progress cho Dịch Offline ---
async function pollTranslationProgress(gameId, btnElement) {
    try {
        const status = await apiGet(`games/translation-status?game_id=${gameId}`);
        if (status.done) {
            btnElement.disabled = false;
            if (status.error) {
                showToast('❌ ' + status.message, true);
                btnElement.innerText = '▶ Start Translation';
                btnElement.classList.remove('running');
            } else {
                showToast('✅ ' + status.message);
                btnElement.innerText = '⏹ Stop Game';
            }
            return;
        }

        let pct = 0;
        if (status.total > 0) {
            pct = Math.round((status.progress / status.total) * 100);
        }
        btnElement.innerText = `${pct}% Đang dịch...`;
        
        // Tiếp tục poll sau 1 giây
        setTimeout(() => pollTranslationProgress(gameId, btnElement), 1000);
    } catch (e) {
        console.error('Polling error:', e);
        setTimeout(() => pollTranslationProgress(gameId, btnElement), 2000);
    }
}

// --- Delete Game ---
async function deleteGame(gameId) {
    if (!confirm('Bạn chắc chắn muốn xóa game này?')) return;

    try {
        const result = await apiPost('games/delete', { game_id: gameId });
        if (result.status === 'success') {
            showToast('🗑 Đã xóa game');
            // Xóa card khỏi DOM ngay lập tức
            const card = document.getElementById(`card-${gameId}`);
            if (card) {
                card.style.transition = 'opacity 0.3s, transform 0.3s';
                card.style.opacity = '0';
                card.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    card.remove();
                    // Nếu không còn card nào, reload để hiện empty state
                    const container = document.getElementById('games-container');
                    if (container && container.children.length === 0) {
                        loadGames();
                    }
                }, 300);
            }
        } else {
            showToast('❌ ' + (result.error || 'Lỗi không xác định'), true);
        }
    } catch (e) {
        showToast('❌ Lỗi: ' + e, true);
    }
}

// --- Toast Notification ---
function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-message');
    if (!toast || !msg) return;

    msg.innerText = message;
    toast.style.borderColor = isError ? 'var(--danger)' : 'var(--accent)';
    toast.style.color = isError ? 'var(--danger)' : 'var(--text-primary)';

    toast.classList.add('show');
    clearTimeout(window._toastTimer);
    window._toastTimer = setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
