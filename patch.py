import os

js_code = """
let currentGlossaryGameId = null;
let currentGlossaryData = {};

function openGlossaryModal(gameId) {
    currentGlossaryGameId = gameId;
    const btn = document.querySelector(`button[onclick="openGlossaryModal('${gameId}')"]`);
    if (btn && btn.parentElement.dataset.glossary) {
        currentGlossaryData = JSON.parse(btn.parentElement.dataset.glossary);
    } else {
        currentGlossaryData = {};
    }
    renderGlossaryList();
    document.getElementById('glossary-modal').style.display = 'flex';
}

function closeGlossaryModal() {
    document.getElementById('glossary-modal').style.display = 'none';
}

function renderGlossaryList() {
    const list = document.getElementById('glossary-list');
    list.innerHTML = '';
    for (const [src, tgt] of Object.entries(currentGlossaryData)) {
        const row = document.createElement('div');
        row.style = "display: flex; gap: 8px; margin-bottom: 8px;";
        row.innerHTML = `
            <input type="text" class="themed-input" value="${src}" readonly style="flex: 1; padding: 4px; border-radius: 4px;">
            <input type="text" class="themed-input" value="${tgt}" readonly style="flex: 1; padding: 4px; border-radius: 4px;">
            <button class="btn-delete" style="padding: 4px 8px;" onclick="removeGlossaryEntry('${src}')">X</button>
        `;
        list.appendChild(row);
    }
}

function addGlossaryEntry() {
    const srcInput = document.getElementById('glossary-source');
    const tgtInput = document.getElementById('glossary-target');
    const src = srcInput.value.trim();
    const tgt = tgtInput.value.trim();
    if (src && tgt) {
        currentGlossaryData[src] = tgt;
        srcInput.value = '';
        tgtInput.value = '';
        renderGlossaryList();
    }
}

function removeGlossaryEntry(src) {
    delete currentGlossaryData[src];
    renderGlossaryList();
}

async function saveGlossary() {
    try {
        const res = await apiPost('games/update-settings', {
            game_id: currentGlossaryGameId,
            glossary: currentGlossaryData
        });
        if (res.status === 'success') {
            showToast('Đã lưu Từ điển cá nhân!');
            closeGlossaryModal();
            loadGames();
        } else {
            showToast('Lỗi lưu từ điển', true);
        }
    } catch(e) {
        showToast('Lỗi kết nối', true);
    }
}
"""

with open('atm/ui/web/script.js', 'ab') as f:
    f.write(js_code.encode('utf-8'))
