window.ATM = window.ATM || {};
window.ATM.core = window.ATM.core || {};

/**
 * ATM.i18n - Core Translation System
 * Quản lý ngôn ngữ nội địa hóa (Anh/Việt)
 */
(function() {
    const dict = {
        'vi': {
            'common.save': 'Lưu',
            'common.cancel': 'Hủy',
            'common.delete': 'Xóa',
            'common.close': 'Đóng',
            'common.error': 'Lỗi',
            'common.success': 'Thành công',
            'status.running': 'Đang dịch...',
            'status.completed': 'Hoàn thành',
            'status.failed': 'Lỗi dịch thuật',
            'status.interrupted': 'Bị gián đoạn',
            'toast.settings_saved': 'Đã lưu cấu hình',
            'toast.network_error': 'Lỗi kết nối mạng',
            'toast.cache_cleared': 'Đã dọn dẹp Cache',
            'toast.tm_cleared': 'Đã xóa TM',
            'toast.stats_refreshed': 'Đã làm mới dữ liệu',
            
            // From old app.js
            "menu.library": "Thư viện",
            "menu.plugins": "Bổ trợ",
            "menu.settings": "Cài đặt",
            "menu.add_game": "Thêm Game",
            "menu.exit": "Thoát",
            "menu.exit_confirm": "Bạn có chắc chắn muốn thoát ứng dụng?",
            "library.title": "Thư viện Game",
            "library.subtitle": "Quản lý và khởi chạy game dịch tự động",
            "plugins.title": "Kho bổ trợ",
            "plugins.subtitle": "Cài đặt và quản lý bộ máy dịch",
            "plugins.google_desc": "Miễn phí, nhanh, không cần API key.",
            "plugins.installed": "Đã cài",
            "plugins.deepl_desc": "Chất lượng dịch cao. Cần nhập API key.",
            "plugins.ready": "Sẵn sàng",
            "plugins.deepl_placeholder": "Nhập DeepL API Key...",
            "plugins.libre_desc": "Mã nguồn mở, tự host được, hoàn toàn miễn phí.",
            "plugins.coming_soon": "Sắp có",
            "settings.title": "Cài đặt",
            "settings.subtitle": "Tùy chỉnh trải nghiệm Launcher",
            "settings.dark_mode": "Giao diện tối (Dark Mode)",
            "settings.dark_mode_desc": "Bật/tắt chế độ màn hình nền tối.",
            "settings.accent_color": "Màu chủ đạo",
            "settings.accent_color_desc": "Tùy chỉnh màu sắc cá nhân hóa cho Launcher.",
            "settings.ui_lang": "Ngôn ngữ giao diện",
            "settings.ui_lang_desc": "Chọn ngôn ngữ hiển thị cho Launcher.",
            "settings.tm_threshold": "Ngưỡng Translation Memory",
            "settings.tm_threshold_desc": "Chỉ hiện gợi ý khi độ tương đồng lớn hơn hoặc bằng mức này. Các gợi ý không bao giờ tự động áp dụng.",
            "library.empty_title": "Chưa có game nào",
            "library.empty_desc": "Bấm \"+ Thêm Game\" để bắt đầu.",
            "glossary.title": "Từ điển cá nhân",
            "glossary.desc": "Thêm các cặp từ để không bị dịch sai (VD: Tên nhân vật, Chiêu thức). Từ điển áp dụng riêng cho game này.",
            "card.engine": "Engine Dịch",
            "card.source_lang": "Ngôn ngữ gốc",
            "card.target_lang": "Dịch sang",
            "card.start": "Bắt đầu dịch",
            "card.stop": "Dừng Game",
            "card.stopping": "Đang dừng...",
            "card.initializing": "Đang khởi tạo...",
            "card.translating": "đang dịch",
            "card.glossary_tooltip": "Từ điển cá nhân",
            "card.editor_tooltip": "Chỉnh sửa văn bản",
            "card.delete_tooltip": "Xóa game",
            "toast.lang_updated": "Đã cập nhật ngôn ngữ",
            "toast.lang_error": "Lỗi cập nhật ngôn ngữ",
            "toast.game_stopped": "Game đã dừng",
            "toast.game_started": "Game đã khởi chạy! Bấm lại để dừng.",
            "toast.translating": "Đang tiến hành dịch offline... Bấm Stop để huỷ.",
            "toast.no_deepl_key": "Lỗi: Bạn chưa nhập DeepL API Key trong mục Cài đặt / Bổ trợ!",
            "toast.game_deleted": "Đã xóa game",
            "toast.unknown_error": "Lỗi không xác định",
            "toast.glossary_saved": "Đã lưu Từ điển cá nhân!",
            "toast.glossary_error": "Lỗi lưu từ điển",
            "toast.connection_error": "Lỗi kết nối",
            "toast.stats_refreshed": "Đã làm mới thống kê",
            "toast.stats_error": "Lỗi tải dữ liệu Data",
            "toast.clear_cache_error": "Lỗi khi xóa cache",
            "toast.tm_cleared": "Đã xóa Translation Memory",
            "toast.tm_error": "Lỗi khi xóa Memory",
            "toast.opening_folder": "Đang mở thư mục Data...",
            "editor.title": "Trình quản lý Cache",
            "editor.search_placeholder": "Tìm kiếm văn bản gốc hoặc bản dịch...",
            "editor.hint": "*Sửa trực tiếp bản dịch ở đây sẽ có tác dụng ngay lập tức cho lần dịch tiếp theo.",
            "btn.add": "Thêm",
            "tm.title": "Gợi ý Translation Memory",
            "tm.desc": "Gợi ý cần được bạn xác nhận trước khi lưu hoặc sử dụng.",
            "tm.lookup_placeholder": "Nhập văn bản cần tra cứu...",
            "tm.category": "Phân loại",
            "tm.find_btn": "Tìm gợi ý",
            "btn.close": "Đóng",
            "btn.save": "Lưu thay đổi",
            "confirm.exit": "Bạn có chắc chắn muốn thoát Auto Translator Manager?",
            "confirm.delete": "Bạn có chắc chắn muốn xóa game này?",
            "confirm.clear_cache": "Bạn có chắc chắn muốn xóa Cache?",
            "confirm.clear_tm": "Bạn có chắc chắn muốn xóa TOÀN BỘ Translation Memory?",
            "confirm.yes": "Đồng ý",
            "confirm.no": "Hủy",
            "goodbye.message": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
            "toast.shutting_down": "Đang tắt ứng dụng...",
            "confirm.delete_game": "Bạn chắc chắn muốn xóa game này?",
            "menu.data": "Dữ liệu",
            "data.title": "Quản lý Dữ liệu",
            "data.subtitle": "Quản lý bộ nhớ cache và dữ liệu dịch thuật",
            "data.open_folder": "Mở thư mục Data",
            "data.refresh": "Làm mới thống kê",
            "data.global_cache": "Global Translation Cache",
            "data.global_cache_desc": "Bộ nhớ đệm chứa các câu dịch tự động từ API.",
            "data.entries": "Mục (Entries)",
            "data.size": "Kích thước (Size)",
            "data.keep_clear": "Xóa & Giữ lại N câu",
            "data.clear_all": "Xóa Hết",
            "data.global_tm": "Global Translation Memory",
            "data.global_tm_desc": "Bộ nhớ từ vựng đã được người dùng xác nhận.",
            "data.game_data": "Dữ liệu theo Game (Game Data)",
            "glossary.source_placeholder": "Từ gốc (bất kỳ ngôn ngữ)",
            "glossary.target_placeholder": "Dịch thành",
            
            // New additions
            "hello.loading": "Khởi tạo hệ thống...",
            "goodbye.title": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
            "goodbye.subtitle": "Đang lưu cài đặt và tắt hệ thống...",
            "dashboard.empty_title": "Chưa có game nào",
            "dashboard.empty_desc": "Bấm \"+ Thêm Game\" để bắt đầu."
        },
        'en': {
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.delete': 'Delete',
            'common.close': 'Close',
            'common.error': 'Error',
            'common.success': 'Success',
            'status.running': 'Translating...',
            'status.completed': 'Completed',
            'status.failed': 'Translation Failed',
            'status.interrupted': 'Interrupted',
            'toast.settings_saved': 'Settings saved',
            'toast.network_error': 'Network error',
            'toast.cache_cleared': 'Cache cleared',
            'toast.tm_cleared': 'TM cleared',
            'toast.stats_refreshed': 'Data refreshed',
            'dashboard.empty_title': 'No games found',
            'dashboard.empty_desc': 'Click "+ Add Game" to get started.',

            // Modals & Forms
            "editor.title": "Cache Manager",
            "editor.search_placeholder": "Search original text or translation...",
            "editor.hint": "*Editing translations here will take effect immediately on the next translation.",
            "btn.add": "Add",
            "tm.title": "Translation Memory Suggestions",
            "tm.desc": "Suggestions need your confirmation before saving or applying.",
            "tm.lookup_placeholder": "Enter text to lookup...",
            "tm.category": "Category",
            "tm.find_btn": "Find Suggestions",
            "btn.close": "Close",
            "btn.save": "Save Changes",
            "confirm.exit": "Are you sure you want to exit Auto Translator Manager?",
            "confirm.delete": "Are you sure you want to delete this game?",
            "confirm.clear_cache": "Are you sure you want to clear the Cache?",
            "confirm.clear_tm": "Are you sure you want to clear ALL Translation Memory?",
            "confirm.yes": "Yes",
            "confirm.no": "No",
            "goodbye.message": "Thank you for using ATM. See you again!",
            "toast.shutting_down": "Shutting down...",
            "confirm.delete_game": "Are you sure you want to delete this game?",
            "menu.data": "Data",
            "data.title": "Data Management",
            "data.subtitle": "Manage cache and translation data",
            "data.open_folder": "Open Data Folder",
            "data.refresh": "Refresh Stats",
            "data.global_cache": "Global Translation Cache",
            "data.global_cache_desc": "Cache containing automated translations from the API.",
            "data.entries": "Entries",
            "data.size": "Size",
            "data.keep_clear": "Clear & Keep N lines",
            "data.clear_all": "Clear All",
            "data.global_tm": "Global Translation Memory",
            "data.global_tm_desc": "Vocabulary memory confirmed by the user.",
            "data.game_data": "Game Data",
            "glossary.title": "Personal Glossary",
            "glossary.desc": "Add word pairs to prevent mistranslations.",
            "glossary.source_placeholder": "Original word (any language)",
            "glossary.target_placeholder": "Translate to",
            "hello.loading": "Initializing system...",
            "goodbye.title": "Thank you for using ATM. See you again!",
            "goodbye.subtitle": "Saving settings and shutting down...",
            
            // From old app.js
            "menu.library": "Library",
            "menu.plugins": "Plugins",
            "menu.settings": "Settings",
            "menu.add_game": "Add Game",
            "menu.exit": "Exit",
            "menu.exit_confirm": "Are you sure you want to exit the application?",
            "library.title": "My Library",
            "library.subtitle": "Manage and launch auto-translated games",
            "plugins.title": "Plugin Marketplace",
            "plugins.subtitle": "Install and manage translation engines",
            "plugins.google_desc": "Free, fast, no API key required.",
            "plugins.installed": "Installed",
            "plugins.deepl_desc": "High quality translation. API key required.",
            "plugins.ready": "Ready",
            "plugins.deepl_placeholder": "Enter DeepL API Key...",
            "plugins.libre_desc": "Open source, self-hosted, completely free.",
            "plugins.coming_soon": "Coming Soon",
            "settings.title": "Settings",
            "settings.subtitle": "Customize Launcher Experience",
            "settings.dark_mode": "Dark Mode",
            "settings.dark_mode_desc": "Toggle dark background mode.",
            "settings.accent_color": "Accent Color",
            "settings.accent_color_desc": "Customize personalized color for the Launcher.",
            "settings.ui_lang": "UI Language",
            "settings.ui_lang_desc": "Select the display language for the Launcher.",
            "settings.tm_threshold": "Translation Memory threshold",
            "settings.tm_threshold_desc": "Only show fuzzy suggestions at or above this similarity. Suggestions are never applied automatically.",
            "library.empty_title": "No games found",
            "library.empty_desc": "Click \"+ Add Game\" to get started.",
            "glossary.title": "Custom Glossary",
            "glossary.desc": "Add word pairs to prevent mistranslations (e.g., Character names, Skills). This glossary applies only to this game.",
            "card.engine": "Translation Engine",
            "card.source_lang": "Source Language",
            "card.target_lang": "Target Language",
            "card.start": "Start Translation",
            "card.stop": "Stop Game",
            "card.stopping": "Stopping...",
            "card.initializing": "Initializing...",
            "card.translating": "translating",
            "card.glossary_tooltip": "Custom Glossary",
            "card.editor_tooltip": "Text Editor",
            "card.delete_tooltip": "Delete game",
            "toast.lang_updated": "Language updated",
            "toast.lang_error": "Failed to update language",
            "toast.game_stopped": "Game stopped",
            "toast.game_started": "Game launched! Click again to stop.",
            "toast.translating": "Offline translation in progress... Press Stop to cancel.",
            "toast.no_deepl_key": "Error: DeepL API Key not found. Enter it in Settings / Plugins!",
            "toast.game_deleted": "Game deleted",
            "toast.unknown_error": "Unknown error",
            "toast.glossary_saved": "Glossary saved!",
            "toast.glossary_error": "Failed to save glossary",
            "toast.connection_error": "Connection error",
            "toast.stats_refreshed": "Stats refreshed",
            "toast.stats_error": "Failed to load Data",
            "toast.clear_cache_error": "Failed to clear cache",
            "toast.tm_cleared": "Translation Memory cleared",
            "toast.tm_error": "Failed to clear Memory",
            "toast.opening_folder": "Opening Data folder...",
            "editor.title": "Grid Editor",
            "editor.search_placeholder": "Search...",
            "editor.hint": "*Direct edits here apply immediately to the next translation.",
            "btn.add": "Add",
            "tm.title": "Translation Memory suggestions",
            "tm.desc": "Suggestions need your confirmation before they are saved or used.",
            "tm.lookup_placeholder": "Text to look up",
            "tm.category": "Category",
            "tm.find_btn": "Find suggestions",
            "btn.close": "Close",
            "btn.save": "Save",
            "confirm.exit": "Are you sure you want to exit Auto Translator Manager?",
            "confirm.delete": "Are you sure you want to delete this game?",
            "confirm.clear_cache": "Are you sure you want to clear Cache?",
            "confirm.clear_tm": "Are you sure you want to clear ALL Translation Memory?",
            "confirm.yes": "Yes",
            "confirm.no": "Cancel",
            "goodbye.message": "Thank you for using ATM. See you again!",
            "toast.shutting_down": "Shutting down...",
            "menu.data": "Data",
            "data.title": "Data Management",
            "data.subtitle": "Manage cache and translation memory",
            "data.open_folder": "Open Data Folder",
            "data.refresh": "Refresh Stats",
            "data.global_cache": "Global Translation Cache",
            "data.global_cache_desc": "API-translated strings cache",
            "data.entries": "Entries",
            "data.size": "Size",
            "data.keep_clear": "Keep & Clear",
            "data.clear_all": "Clear All",
            "data.global_tm": "Translation Memory",
            "data.global_tm_desc": "User-confirmed translations",
            "glossary.source_placeholder": "Source word",
            "glossary.target_placeholder": "Target translation",
            
            // New additions
            "hello.loading": "Initializing system...",
            "goodbye.title": "Thank you for using ATM. See you again!",
            "goodbye.subtitle": "Saving settings and shutting down..."
        }
    };

    let currentLang = localStorage.getItem('atm_lang') || 'vi';

    window.ATM.i18n = {
        /**
         * Lấy câu dịch theo key
         */
        t: function(key, params = {}) {
            let text = dict[currentLang] && dict[currentLang][key];
            if (text === undefined) return undefined;
            for (const [k, v] of Object.entries(params)) {
                text = text.replace(new RegExp(`{${k}}`, 'g'), v);
            }
            return text;
        },

        /**
         * Đổi ngôn ngữ
         */
        setLang: function(lang) {
            if (dict[lang]) {
                currentLang = lang;
                localStorage.setItem('atm_lang', lang);
                this.updateDOM();
            }
        },

        /**
         * Lấy ngôn ngữ hiện tại
         */
        getLang: function() {
            return currentLang;
        },

        /**
         * Cập nhật toàn bộ thẻ HTML có data-i18n
         */
        updateDOM: function() {
            if (window.ATM.dom) {
                const els = window.ATM.dom.query('[data-i18n]');
                els.forEach(el => {
                    const key = el.dataset.i18n;
                    window.ATM.dom.text(el, this.t(key));
                });
                
                // Cập nhật cả placeholder
                const placeholders = window.ATM.dom.query('[data-i18n-placeholder]');
                placeholders.forEach(el => {
                    const key = el.dataset.i18nPlaceholder;
                    el.placeholder = this.t(key);
                });
            }
        },
        
        /**
         * Hàm này để các script khác báo cần update UI
         */
        updateUI: function() {
            this.updateDOM();
        }
    };
})();

