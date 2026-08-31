window.ATM = window.ATM || {};
window.ATM.core = window.ATM.core || {};

/**
 * ATM.i18n - Core Translation System
 * Quản lý ngôn ngữ nội địa hóa (Anh/Việt)
 */
(function() {
    const dict = {
        'vi': {
            // === COMMON ===
            'common.save': 'Lưu',
            'common.cancel': 'Hủy',
            'common.delete': 'Xóa',
            'common.close': 'Đóng',
            'common.error': 'Lỗi',
            'common.success': 'Thành công',

            // === STATUS ===
            'status.running': 'Đang dịch...',
            'status.completed': 'Hoàn thành',
            'status.failed': 'Lỗi dịch thuật',
            'status.interrupted': 'Bị gián đoạn',

            'editor.loading': 'Đang tải dữ liệu...',
            'editor.accept': 'Chấp nhận',
            'editor.source_lang': 'Ngôn ngữ Gốc (Source)',
            'editor.target_lang': 'Bản Dịch (Target)',
            'editor.stats': 'Thống kê',
            'editor.prev_page': 'Trang trước',
            'editor.next_page': 'Trang sau',
            
            'common.info': 'Thông báo',
            'workspace.sync_btn_title': 'Đồng bộ lại dữ liệu dịch',
            'workspace.status_ready': 'Sẵn sàng',
            'workspace.refreshing': 'Đang đồng bộ dữ liệu...',
            
            'confirm.sync_translation': 'Đồng bộ dữ liệu dịch?',
            'workspace.sync_success': 'Đã đồng bộ dữ liệu dịch',
            'error.sync_failed': 'Đồng bộ dữ liệu thất bại',
            'status.paused': 'Tạm dừng',
            'toast.settings_error': 'Lỗi lưu cấu hình',
            'toast.initializing': 'Đang khởi tạo...',
            'data.game_data_placeholder': 'Dữ liệu game...',
            'plugins.deepl': 'DeepL API',
            'plugins.libre': 'LibreTranslate',
            'editor.total_items': 'Tổng: {total} mục',
            'tm.no_results': 'Không tìm thấy kết quả',

            'lang.auto': 'Tự động phát hiện',
            'lang.ja': 'Tiếng Nhật',
            'lang.en': 'Tiếng Anh',
            'lang.zh': 'Tiếng Trung (Giản thể)',
            'lang.zh-TW': 'Tiếng Trung (Phồn thể)',
            'lang.ko': 'Tiếng Hàn',
            'lang.vi': 'Tiếng Việt',
            'lang.th': 'Tiếng Thái',
            'lang.id': 'Tiếng Indonesia',
            'lang.ms': 'Tiếng Mã Lai',
            'lang.google': 'Google Translate',
            'lang.deepl': 'DeepL API',

            'toast.add_game_success': 'Thêm game thành công!',
            'toast.add_game_error': 'Lỗi thêm game',
            'toast.delete_success': 'Đã xóa game',
            'toast.play_failed': 'Lỗi khởi chạy game. Vui lòng thử lại!',
            'toast.start_failed': 'Lỗi khởi động',
            'card.start': 'Bắt đầu dịch',
            'card.stop': 'Dừng',
            'card.resume': 'Tiếp tục (Lỗi/Khởi động lại)',
            'card.play': 'Chơi Game',
            'workspace.status_ready': 'Sẵn sàng',
            'dashboard.empty_title': 'Không tìm thấy game nào',
            'dashboard.empty_desc': 'Bấm "+ Thêm Game" để bắt đầu.',
            'data.loading': 'Đang tải dữ liệu...',
            'editor.qa_running': 'Đang quét...',
            'editor.qa_found': 'Phát hiện {count} lỗi QA!',
            'editor.qa_clean': 'Tuyệt vời! Không phát hiện lỗi QA nào.',
            'editor.qa_error': 'Lỗi khi chạy QA',
            'editor.apply_success': 'Đã áp dụng gợi ý',
            'editor.apply_error': 'Lỗi lưu gợi ý',
            'editor.empty': 'Không có dữ liệu.',
            'editor.save_error': 'Không thể lưu bản dịch. Đã khôi phục lại.',
            'glossary.add_success': 'Đã thêm từ',
            'glossary.add_error': 'Lỗi thêm từ',
            'glossary.export_success': 'Đã tải xuống file CSV',
            'glossary.export_error': 'Lỗi khi xuất Glossary',
            'glossary.import_confirm': 'Preview Import:\n- {new} Mới\n- {conflict} Xung đột\n- {duplicate} Trùng lặp\n- {invalid} Không hợp lệ.\n\nBạn có muốn Ghi đè (Merge) không?',
            'glossary.import_success': 'Đã import Glossary thành công',
            'glossary.import_error': 'Lỗi Import',
            'plugins.deepl_configured': 'Đã cấu hình',
            'plugins.deepl_placeholder': 'Nhập API Key (tùy chọn)',
            'card.delete_confirm': 'Bạn chắc chắn muốn xóa game này?',

            // === MENU ===
            "menu.library": "Thư viện",
            "menu.plugins": "Bổ trợ",
            "menu.settings": "Cài đặt",
            "menu.add_game": "Thêm Game",
            "menu.exit": "Thoát",
            "menu.exit_confirm": "Bạn có chắc chắn muốn thoát ứng dụng?",
            "menu.data": "Dữ liệu",

            // === LIBRARY ===
            "library.title": "Thư viện Game",
            "library.subtitle": "Quản lý và khởi chạy game dịch tự động",
            "library.empty_title": "Chưa có game nào",
            "library.empty_desc": "Bấm \"+ Thêm Game\" để bắt đầu.",
            "dashboard.empty_title": "Chưa có game nào",
            "dashboard.empty_desc": "Bấm \"+ Thêm Game\" để bắt đầu.",

            // === PLUGINS ===
            "plugins.title": "Kho bổ trợ",
            "plugins.subtitle": "Cài đặt và quản lý bộ máy dịch",
            "plugins.google_desc": "Miễn phí, nhanh, không cần API key.",
            "plugins.installed": "Đã cài",
            "plugins.deepl_desc": "Chất lượng dịch cao. Cần nhập API key.",
            "plugins.ready": "Sẵn sàng",
            "plugins.deepl_placeholder": "Nhập DeepL API Key...",
            "plugins.libre_desc": "Mã nguồn mở, tự host được, hoàn toàn miễn phí.",
            "plugins.coming_soon": "Sắp có",

            // === SETTINGS ===
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

            // === GAME CARD ===
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

            // === TOAST ===
            'toast.settings_saved': 'Đã lưu cấu hình',
            'toast.network_error': 'Lỗi kết nối mạng',
            'toast.cache_cleared': 'Đã dọn dẹp Cache',
            'toast.tm_cleared': 'Đã xóa Translation Memory',
            'toast.stats_refreshed': 'Đã làm mới thống kê',
            "toast.lang_updated": "Đã cập nhật ngôn ngữ",
            "toast.lang_error": "Lỗi cập nhật ngôn ngữ",
            "toast.game_stopped": "Game đã dừng",
            "toast.game_started": "Game đã khởi chạy! Bấm lại để dừng.",
            "toast.translating": "Đang tiến hành dịch offline... Bấm Stop để huỷ.",
            "toast.no_deepl_key": "Lỗi: Bạn chưa nhập DeepL API Key trong mục Cài đặt / Bổ trợ!",
            "toast.game_deleted": "Game đã bị xóa",
            "toast.unknown_error": "Lỗi không xác định",
            "toast.start_failed": "Lỗi khởi chạy",
            "toast.play_failed": "Không thể khởi chạy game. Vui lòng thử lại!",
            "toast.server_error": "Lỗi xử lý từ máy chủ",
            "toast.glossary_saved": "Đã lưu từ điển cá nhân!",
            "toast.glossary_error": "Lỗi lưu từ điển",
            "toast.connection_error": "Lỗi kết nối",
            "toast.stats_error": "Lỗi tải dữ liệu Data",
            "toast.clear_cache_error": "Lỗi khi xóa cache",
            "toast.tm_error": "Lỗi khi xóa Memory",
            "toast.opening_folder": "Đang mở thư mục Data...",
            "toast.add_game_success": "Đã thêm game thành công!",
            "toast.duplicate_game": "Game này đã được thêm vào hệ thống trước đó!",
            "toast.shutting_down": "Đang tắt ứng dụng...",
            "toast.delete_error": "Lỗi khi xóa",

            // === CONFIRM DIALOGS ===
            "confirm.exit": "Bạn có chắc chắn muốn thoát Auto Translator Manager?",
            "confirm.delete": "Bạn có chắc chắn muốn xóa game này?",
            "confirm.delete_game": "Bạn chắc chắn muốn xóa game này?",
            "confirm.delete_glossary": "Bạn có chắc chắn muốn xóa từ: {word}?",
            "confirm.clear_cache": "Bạn có chắc chắn muốn xóa Cache?",
            "confirm.clear_tm": "Bạn có chắc chắn muốn xóa TOÀN BỘ Translation Memory?",
            "confirm.yes": "Đồng ý",
            "confirm.no": "Hủy",
            "confirm.ok": "OK",

            // === BUTTONS ===
            "btn.add": "Thêm",
            "btn.close": "Đóng",
            "btn.save": "Lưu thay đổi",
            "btn.delete": "Xóa",

            // === EDITOR ===
            "editor.title": "Trình quản lý Cache",
            "editor.search_placeholder": "Tìm kiếm văn bản gốc hoặc bản dịch...",
            "editor.hint": "*Sửa trực tiếp bản dịch ở đây sẽ có tác dụng ngay lập tức cho lần dịch tiếp theo.",
            "editor.filter_all": "Tất cả",
            "editor.filter_qa": "Lỗi QA",
            "editor.run_qa": " Chạy QA Scanner",

            // === GLOSSARY ===
            "glossary.title": "Từ điển cá nhân (Glossary)",
            "glossary.desc": "Thêm các cặp từ để không bị dịch sai (VD: Tên nhân vật, Chiêu thức). Từ điển áp dụng riêng cho game này.",
            "glossary.source_placeholder": "Từ gốc (bất kỳ ngôn ngữ)",
            "glossary.target_placeholder": "Dịch thành",
            "glossary.import": " Nhập (Import)",
            "glossary.export": " Xuất (Export)",

            // === TRANSLATION MEMORY ===
            "tm.title": "Gợi ý Translation Memory",
            "tm.desc": "Gợi ý cần được bạn xác nhận trước khi lưu hoặc sử dụng.",
            "tm.lookup_placeholder": "Nhập văn bản cần tra cứu...",
            "tm.search_placeholder": "Nhập văn bản cần tìm...",
            "tm.category": "Phân loại",
            "tm.find_btn": "Tìm gợi ý",
            "tm.btn_search": "Tìm gợi ý",

            // === WORKSPACE ===
            "workspace.tab_editor": "Editor",
            "workspace.tab_glossary": "Thuật ngữ (Glossary)",
            "workspace.tab_tm": "Bộ nhớ dịch (TM)",
            "workspace.tab_audit": "Coverage Audit",
            "workspace.tab_extract": "Extract Offline",
            "workspace.back": "Trở về Thư viện",

            // === DATA ===
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
            "data.game_data_title": "Dữ liệu theo Game (Game Data)",
            "data.clear_all_confirm": "Bạn có chắc chắn muốn xóa toàn bộ Cache?",
            "data.clear_tm_confirm": "Bạn có chắc chắn muốn xóa toàn bộ Translation Memory?",


            // === MISC ===
            "error.engine_not_supported": "Lỗi: Hệ thống chưa hỗ trợ tự động dịch cho Engine này ({engine}). Vui lòng chọn game Unity, RPG Maker hoặc RenPy.",
            "hello.loading": "Khởi tạo hệ thống...",
            "goodbye.title": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
            "goodbye.subtitle": "Đang lưu cài đặt và tắt hệ thống...",
            "goodbye.message": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
        },
        'en': {
            // === COMMON ===
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.delete': 'Delete',
            'common.close': 'Close',
            'common.error': 'Error',
            'common.success': 'Success',

            // === STATUS ===
            'status.running': 'Translating...',
            'status.completed': 'Completed',
            'status.failed': 'Translation Failed',
            'status.interrupted': 'Interrupted',

            'editor.loading': 'Loading data...',
            'editor.accept': 'Accept',
            'editor.source_lang': 'Source Language',
            'editor.target_lang': 'Target Language',
            'editor.stats': 'Statistics',
            'editor.prev_page': 'Prev Page',
            'editor.next_page': 'Next Page',
            
            'common.info': 'Information',
            'workspace.sync_btn_title': 'Sync translation data',
            'workspace.status_ready': 'Ready',
            'workspace.refreshing': 'Syncing data...',

            'confirm.sync_translation': 'Sync translation data?',
            'workspace.sync_success': 'Translation data synced',
            'error.sync_failed': 'Sync failed',
            'status.paused': 'Paused',
            'toast.settings_error': 'Error saving settings',
            'toast.initializing': 'Initializing...',
            'data.game_data_placeholder': 'Game data...',
            'plugins.deepl': 'DeepL API',
            'plugins.libre': 'LibreTranslate',
            'editor.total_items': 'Total: {total} items',
            'tm.no_results': 'No results found',

            'lang.auto': 'Auto Detect',
            'lang.ja': 'Japanese',
            'lang.en': 'English',
            'lang.zh': 'Chinese (Simplified)',
            'lang.zh-TW': 'Chinese (Traditional)',
            'lang.ko': 'Korean',
            'lang.vi': 'Vietnamese',
            'lang.th': 'Thai',
            'lang.id': 'Indonesian',
            'lang.ms': 'Malay',
            'lang.google': 'Google Translate',
            'lang.deepl': 'DeepL API',

            // === MENU ===
            "menu.library": "Library",
            "menu.plugins": "Plugins",
            "menu.settings": "Settings",
            "menu.add_game": "Add Game",
            "menu.exit": "Exit",
            "menu.exit_confirm": "Are you sure you want to exit the application?",
            "menu.data": "Data",

            // === LIBRARY ===
            "library.title": "My Library",
            "library.subtitle": "Manage and launch auto-translated games",
            "library.empty_title": "No games found",
            "library.empty_desc": "Click \"+ Add Game\" to get started.",
            "dashboard.empty_title": "No games found",
            "dashboard.empty_desc": "Click \"+ Add Game\" to get started.",

            // === PLUGINS ===
            "plugins.title": "Plugin Marketplace",
            "plugins.subtitle": "Install and manage translation engines",
            "plugins.google_desc": "Free, fast, no API key required.",
            "plugins.installed": "Installed",
            "plugins.deepl_desc": "High quality translation. API key required.",
            "plugins.ready": "Ready",
            "plugins.deepl_placeholder": "Enter DeepL API Key...",
            "plugins.libre_desc": "Open source, self-hosted, completely free.",
            "plugins.coming_soon": "Coming Soon",

            // === SETTINGS ===
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

            // === GAME CARD ===
            "card.engine": "Translation Engine",
            "card.source_lang": "Source Language",
            "card.target_lang": "Target Language",
            "card.start": "Start Translation",
            "card.stop": "Stop Game",
            "card.stopping": "Stopping...",
            "card.initializing": "Initializing...",
            "card.play": "Play Game",
            "workspace.status_ready": "Ready",
            "card.translating": "translating",
            "card.glossary_tooltip": "Custom Glossary",
            "card.editor_tooltip": "Text Editor",
            "card.delete_tooltip": "Delete game",

            // === TOAST ===
            'toast.settings_saved': 'Settings saved',
            'toast.network_error': 'Network error',
            'toast.cache_cleared': 'Cache cleared',
            'toast.tm_cleared': 'Translation Memory cleared',
            'toast.stats_refreshed': 'Stats refreshed',
            "toast.lang_updated": "Language updated",
            "toast.lang_error": "Failed to update language",
            "toast.game_stopped": "Game stopped",
            "toast.game_started": "Game launched! Click again to stop.",
            "toast.translating": "Offline translation in progress... Press Stop to cancel.",
            "toast.no_deepl_key": "Error: DeepL API Key not found. Enter it in Settings / Plugins!",
            "toast.game_deleted": "Game deleted",
            "toast.unknown_error": "Unknown error",
            "toast.start_failed": "Failed to start",
            "toast.play_failed": "Failed to launch the game. Please try again!",
            "toast.server_error": "Server processing error",
            "toast.glossary_saved": "Glossary saved!",
            "toast.glossary_error": "Failed to save glossary",
            "toast.connection_error": "Connection error",
            "toast.stats_error": "Failed to load Data",
            "toast.clear_cache_error": "Failed to clear cache",
            "toast.tm_error": "Failed to clear Memory",
            "toast.opening_folder": "Opening Data folder...",
            "toast.add_game_success": "Game added successfully!",
            "toast.duplicate_game": "This game is already in the library!",
            "toast.shutting_down": "Shutting down...",
            "toast.delete_error": "Error deleting",

            // === CONFIRM DIALOGS ===
            "confirm.exit": "Are you sure you want to exit Auto Translator Manager?",
            "confirm.delete": "Are you sure you want to delete this game?",
            "confirm.delete_game": "Are you sure you want to delete this game?",
            "confirm.delete_glossary": "Are you sure you want to delete the word: {word}?",
            "confirm.clear_cache": "Are you sure you want to clear the Cache?",
            "confirm.clear_tm": "Are you sure you want to clear ALL Translation Memory?",
            "confirm.yes": "Yes",
            "confirm.no": "Cancel",
            "confirm.ok": "OK",

            // === BUTTONS ===
            "btn.add": "Add",
            "btn.close": "Close",
            "btn.save": "Save Changes",
            "btn.delete": "Delete",

            // === EDITOR ===
            "editor.title": "Grid Editor",
            "editor.search_placeholder": "Search original text or translation...",
            "editor.hint": "*Direct edits here apply immediately to the next translation.",
            "editor.filter_all": "All",
            "editor.filter_qa": "QA Errors",
            "editor.run_qa": " Run QA Scanner",

            // === GLOSSARY ===
            "glossary.title": "Personal Glossary",
            "glossary.desc": "Add word pairs to prevent mistranslations (e.g., Character names, Skills). This glossary applies only to this game.",
            "glossary.source_placeholder": "Original word (any language)",
            "glossary.target_placeholder": "Translate to",
            "glossary.import": " Import",
            "glossary.export": " Export",

            // === TRANSLATION MEMORY ===
            "tm.title": "Translation Memory Suggestions",
            "tm.desc": "Suggestions need your confirmation before saving or applying.",
            "tm.lookup_placeholder": "Enter text to lookup...",
            "tm.search_placeholder": "Enter text to look up...",
            "tm.category": "Category",
            "tm.find_btn": "Find Suggestions",
            "tm.btn_search": "Find Suggestions",

            // === WORKSPACE ===
            "workspace.tab_editor": "Editor",
            "workspace.tab_glossary": "Glossary",
            "workspace.tab_tm": "Translation Memory",
            "workspace.tab_audit": "Coverage Audit",
            "workspace.tab_extract": "Extract Offline",
            "workspace.back": "Back to Library",

            // === DATA ===
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
            "data.game_data_title": "Game Data",
            "data.clear_all_confirm": "Are you sure you want to clear all Cache?",
            "data.clear_tm_confirm": "Are you sure you want to clear all Translation Memory?",



            // === MISC ===
            "error.engine_not_supported": "Error: Real-time translation is not supported for this Engine ({engine}). Please select a Unity, RPG Maker or RenPy game.",
            "hello.loading": "Initializing system...",
            "goodbye.title": "Thank you for using ATM. See you again!",
            "goodbye.subtitle": "Saving settings and shutting down...",
            "goodbye.message": "Thank you for using ATM. See you again!",
        }
    };

    let currentLang = window.ATM.store.get('atm_lang') || 'vi';

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
                window.ATM.store.set('atm_lang', lang);
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
            if (!window.ATM.dom) return;
            try {
                const els = document.querySelectorAll('[data-i18n]');
                els.forEach(el => {
                    const key = el.getAttribute('data-i18n');
                    if (key) {
                        const val = this.t(key);
                        if (val !== undefined) {
                            // Find the first text node and update it, preserving HTML elements like SVG
                            let textNodeFound = false;
                            for (let i = 0; i < el.childNodes.length; i++) {
                                if (el.childNodes[i].nodeType === Node.TEXT_NODE && el.childNodes[i].nodeValue.trim() !== '') {
                                    el.childNodes[i].nodeValue = val;
                                    textNodeFound = true;
                                    break;
                                }
                            }
                            if (!textNodeFound) {
                                // If no non-empty text node found, either append one or set textContent if empty
                                if (el.childNodes.length === 0) {
                                    el.textContent = val;
                                } else {
                                    el.appendChild(document.createTextNode(' ' + val));
                                }
                            }
                        }
                    }
                });
                
                const placeholders = document.querySelectorAll('[data-i18n-placeholder]');
                placeholders.forEach(el => {
                    const key = el.getAttribute('data-i18n-placeholder');
                    if (key) {
                        const val = this.t(key);
                        if (val !== undefined) el.placeholder = val;
                    }
                });
                
                const titles = document.querySelectorAll('[data-i18n-title]');
                titles.forEach(el => {
                    const key = el.getAttribute('data-i18n-title');
                    if (key) {
                        const val = this.t(key);
                        if (val !== undefined) el.title = val;
                    }
                });
            } catch(e) {
                console.error("i18n Error: ", e);
            }
        },
        
        updateUI: function() {
            this.updateDOM();
        }
    };
})();
