document.addEventListener('DOMContentLoaded', () => {
    
    // --- Navigation Logic ---
    const navLinks = document.querySelectorAll('.nav-links li');
    const viewSections = document.querySelectorAll('.view-section');

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            // Update active state in sidebar
            navLinks.forEach(l => l.classList.remove('active'));
            link.classList.add('active');

            // Show corresponding view
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

    // --- PyWebView Ready Event ---
    window.addEventListener('pywebviewready', () => {
        // Load initial games
        loadGames();

        // Add Game Button Event
        document.getElementById('add-game-btn').addEventListener('click', async () => {
            const result = await window.pywebview.api.add_game();
            if (result && result.status === 'success') {
                showToast(`Added: ${result.game.game_name}`);
                loadGames();
            } else if (result && result.error) {
                showToast(result.error, true);
            }
        });
    });

    // --- API Interactions ---
    async function loadGames() {
        const gamesContainer = document.getElementById('games-container');
        gamesContainer.innerHTML = ''; // Clear current

        const games = await window.pywebview.api.get_games();

        if (!games || games.length === 0) {
            gamesContainer.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
                    <h3>No Games Added</h3>
                    <p style="margin-top: 8px;">Click "+ Add Game" to get started.</p>
                </div>
            `;
            return;
        }

        games.forEach(game => {
            const card = document.createElement('div');
            card.className = 'game-card';
            
            card.innerHTML = `
                <div class="game-info">
                    <h3 title="${game.game_name}">${game.game_name}</h3>
                    <p title="${game.exe_path}">${game.exe_path}</p>
                </div>
                <div class="game-actions">
                    <button class="btn-start" onclick="startGame('${game.id}', this)">Start Translation</button>
                    <button class="btn-delete" onclick="deleteGame('${game.id}')">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            `;
            gamesContainer.appendChild(card);
        });
    }

    window.startGame = async function(gameId, btnElement) {
        if (btnElement.classList.contains('running')) {
            // Stop game logic
            const originalText = btnElement.getAttribute('data-original-text') || "Start Translation";
            btnElement.innerText = "Stopping...";
            await window.pywebview.api.stop_game(gameId);
            btnElement.innerText = originalText;
            btnElement.classList.remove('running');
            showToast("Game stopped");
            return;
        }
        
        // Optimistic UI update
        btnElement.setAttribute('data-original-text', btnElement.innerText);
        btnElement.innerText = "Deploying...";
        btnElement.classList.add('running');
        
        const result = await window.pywebview.api.start_game(gameId);
        
        if (result.status === 'success') {
            showToast("Game launched! Click again to stop.");
            btnElement.innerText = "Stop Game";
        } else {
            showToast("Failed to launch: " + result.error, true);
            btnElement.innerText = btnElement.getAttribute('data-original-text') || "Start Translation";
            btnElement.classList.remove('running');
        }
    };

    window.deleteGame = async function(gameId) {
        if (confirm("Are you sure you want to remove this game?")) {
            await window.pywebview.api.delete_game(gameId);
            showToast("Game removed");
            loadGames();
        }
    };

    // --- Utility ---
    function showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        const msg = document.getElementById('toast-message');
        msg.innerText = message;
        
        if (isError) {
            toast.style.borderColor = "var(--danger)";
            toast.style.color = "var(--danger)";
        } else {
            toast.style.borderColor = "var(--border-color)";
            toast.style.color = "var(--text-primary)";
        }

        toast.classList.add('show');
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
});
