window.ATM = window.ATM || {};
window.ATM.core = window.ATM.core || {};

/**
 * ATM.navigation - Core Routing System
 * Handles switching between Library and Workspace tiers.
 */
(function() {
    function showSection(sectionId) {
        const viewSections = document.querySelectorAll('.view-section');
        viewSections.forEach(view => {
            if (view.id === sectionId) {
                view.classList.remove('hidden');
                view.classList.add('active');
            } else {
                view.classList.remove('active');
                view.classList.add('hidden');
            }
        });
        
        // Update nav links active state
        const navLinks = document.querySelectorAll('.nav-links li');
        navLinks.forEach(link => {
            if (link.dataset.target === sectionId) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    window.ATM.navigation = {
        showLibrary: function() {
            showSection('library-view');
            // Clear workspace state
            sessionStorage.removeItem('atm_current_workspace');
            if (window.ATM.Workspace && typeof window.ATM.Workspace.cleanup === 'function') {
                window.ATM.Workspace.cleanup();
            }
        },
        
        showWorkspace: function(gameId) {
            showSection('workspace-view');
            // Save workspace state
            sessionStorage.setItem('atm_current_workspace', gameId);
        },
        
        showSettings: function() {
            showSection('settings-view');
        },
        
        showData: function() {
            showSection('data-view');
        }
    };
})();
",



