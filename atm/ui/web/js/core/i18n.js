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
            'translation.preparing': 'Đang chuẩn bị dịch...',
            'translation.cancelled': 'Đã hủy dịch',
            'translation.success': 'Dịch hoàn tất',
            'translation.failed': 'Dịch thất bại',
            'translation.rate_limited': 'Bị giới hạn tốc độ API (Rate limit)',
            'translation.error': 'Lỗi trong quá trình dịch',
            'translation.not_running': 'Không có tiến trình dịch nào đang chạy',
            'translation.realtime_running': 'Đang dịch trong game (Real-time)...',
            'translation.realtime_finished': 'Game đã đóng',
            'translation.ready': 'Sẵn sàng',
            'common.lines': 'câu',
            'status.ready': 'Sẵn sàng',
            'toast.game_busy': 'Tiến trình dịch trước đó đang hoàn tất lưu dữ liệu dở dang, vui lòng đợi trong giây lát.',
            'workspace.coverage_title': 'Báo cáo độ phủ {engine}',
            'workspace.coverage_stats': 'Tổng: {total}\nĐã dịch: {translated}\nChưa dịch: {untranslated}\nĐộ phủ: {coverage}%',
            'workspace.audit_failed': 'Lỗi khi kiểm tra độ phủ cho {engine}',
            'workspace.job_already_running': 'Tác vụ đang chạy!',
            'workspace.extract_started': 'Đã bắt đầu trích xuất văn bản.',
            'workspace.extract_completed': 'Trích xuất văn bản hoàn tất!',
            'workspace.extract_failed': 'Trích xuất văn bản thất bại: {status}',
            'workspace.extract_start_error': 'Không thể khởi chạy tác vụ trích xuất.',
            'error.game_not_found': 'Không tìm thấy game trong hệ thống!',
            'error.target_lang_missing': 'Vui lòng chọn ngôn ngữ đích trước khi thực hiện.',
            'toast.delete_running_error': 'Game đang chạy hoặc đang dịch. Vui lòng dừng game trước khi xóa!',
            'toast.clear_running_error': 'Không thể xóa dữ liệu khi game đang dịch. Vui lòng dừng dịch trước!',
            'error.invalid_threshold': 'Ngưỡng Translation Memory phải nằm trong khoảng từ 0 đến 1.',
            'error.cleanup_permission_denied': 'Dọn dẹp thất bại (Từ chối quyền). Vui lòng chạy ATM bằng quyền Administrator. Chi tiết: {details}',
            'error.api_unauthorized': 'Khóa API không hợp lệ hoặc đã hết hạn (HTTP 401/403)!',
            'error.api_rate_limited': 'Bị giới hạn tốc độ yêu cầu (HTTP 429)! Vui lòng chờ vài giây.',
            'error.api_not_found': 'Không tìm thấy mô hình hoặc đường dẫn API (HTTP 404)!',
            'error.api_key_missing': 'Chưa nhập Khóa API. Vui lòng nhập API key trước khi kiểm tra.',
            'error.api_connection_failed': 'Kết nối tới AI thất bại: {error}',
            'error.api_empty_response': 'Mô hình AI trả về kết quả rỗng.',
            'error.invalid_api_key_format': 'Khóa API không hợp lệ: {error}',
            'error.key_too_short_5': 'API Key quá ngắn (tối thiểu 5 ký tự)!',
            'error.key_too_short_deepl': 'DeepL API key quá ngắn (tối thiểu 20 ký tự)!',
            'error.key_too_short_general': 'API Key cho {provider} quá ngắn ({len} ký tự). Khóa thông thường dài ít nhất {min_len} ký tự!',
            'error.cannot_change_engine_while_translating': 'Không thể thay đổi bộ dịch khi đang dịch! Vui lòng dừng tiến trình trước.',

            
            'editor.master_save': 'Lưu các thay đổi',
            'editor.master_cancel': 'Hủy toàn bộ',
            'editor.confirm_discard': 'Bạn có thay đổi chưa lưu. Bạn muốn làm gì?',
            'editor.discard_leave': 'Không Lưu & Rời đi',
            'editor.save_leave': 'Lưu & Rời đi',
            'editor.missing_vars': '⚠️ Cảnh báo: Thiếu biến {vars}',
            'editor.saving': 'Đang lưu...',
            'editor.qa_running': 'Đang quét lỗi...',
            'editor.network_error': 'Lỗi mạng hoặc xung đột dữ liệu',
            'editor.error_load': 'Lỗi tải dữ liệu',
            'editor.keep_mine': 'Giữ bản của tôi (Ghi đè)',
            'editor.use_new': 'Dùng bản mới (Hủy thay đổi)',

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
            'workspace.default_title': 'Không gian làm việc',
            'workspace.default_subtitle': 'Đang tải...',
            
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
            'toast.game_translating': 'Game đang dịch, không thể khởi chạy lúc này!',
            'card.start': 'Bắt đầu dịch',
            'card.stop': 'Dừng',
            'card.resume': 'Tiếp tục (Lỗi/Khởi động lại)',
            'card.play': 'Chơi Game',
            'card.play_now': 'Chơi Game Ngay',
            'card.play_tooltip': 'Chơi Game (Trực tiếp)',
            'card.play_disabled_translating': 'Game đang được dịch, không thể khởi chạy lúc này',
            'card.retranslate': 'Dịch lại',
            'games.btn_sync': 'Đồng bộ & Dịch',
            'games.needs_sync_tooltip': 'Có dữ liệu mới từ Editor/Glossary. Vui lòng bấm để đồng bộ.',
            'workspace.status_ready': 'Sẵn sàng',
            'dashboard.empty_title': 'Không tìm thấy game nào',
            'dashboard.empty_desc': 'Bấm "+ Thêm Game" để bắt đầu.',
            'data.loading': 'Đang tải dữ liệu...',
            'editor.qa_running': 'Đang quét...',
            'editor.qa_found': 'Phát hiện {count} lỗi QA!',
            'editor.qa_clean': 'Tuyệt vời! Không phát hiện lỗi QA nào.',
            'editor.qa_error': 'Lỗi khi chạy QA',
            'editor.qa_no_entries': 'Không có dữ liệu dòng dịch nào để quét QA!',
            'editor.qa_no_translations': 'Chưa có câu nào được dịch để kiểm tra QA. Hãy dịch trước khi quét!',
            'editor.apply_success': 'Đã áp dụng gợi ý',
            'editor.apply_error': 'Lỗi lưu gợi ý',
            'editor.empty': 'Không có dữ liệu.',
            'editor.save_error': 'Không thể lưu bản dịch. Đã khôi phục lại.',
            'editor.batch_save_partial': 'Đã lưu {saved}. Bị lỗi/xung đột: {failed}. Vui lòng thử lại.',
            'glossary.add_success': 'Đã thêm từ',
            'glossary.add_error': 'Lỗi thêm từ',
            'glossary.export_success': 'Đã tải xuống file CSV',
            'glossary.export_error': 'Lỗi khi xuất Glossary',
            'glossary.import_confirm': 'Preview Import:\n- {new} Mới\n- {conflict} Xung đột\n- {duplicate} Trùng lặp\n- {invalid} Không hợp lệ.\n\nBạn có muốn Ghi đè (Merge) không?',
            'glossary.import_success': 'Đã import Glossary thành công',
            'glossary.import_error': 'Lỗi Import',
            'plugins.deepl_configured': 'Đã cấu hình',
            'plugins.deepl_placeholder': 'Nhập API Key (tùy chọn)',
            'card.delete_confirm': 'Bạn có chắc chắn muốn xóa game này? (Sẽ hoàn nguyên file game về nguyên bản)',
            'card.delete_purge_data': 'Xóa vĩnh viễn dữ liệu dịch (Giải phóng ~{size}MB Database). Nếu không tích, dữ liệu sẽ được giữ lại để phục hồi sau này.',
            'games.btn_select': 'Chọn',
            'games.btn_select_all': 'Chọn tất cả',
            'games.btn_deselect_all': 'Bỏ chọn tất cả',
            'games.btn_delete_selected': 'Xóa ({count})',
            'games.btn_cancel_select': 'Hủy',
            'games.delete_multiple_confirm': 'Bạn có chắc chắn muốn xóa {count} game đã chọn? (Sẽ hoàn nguyên file game về nguyên bản)',
            'games.delete_multiple_success': 'Đã xóa thành công {count} game',
            'games.no_game_selected': 'Vui lòng chọn ít nhất một game',
            'app.offline': 'Mất kết nối máy chủ',
            'editor.conflict_msg': 'Dữ liệu trên máy chủ đã thay đổi. Bạn có muốn ghi đè không?',
            'editor.search_draft_warning': 'Bạn có các thay đổi chưa lưu. Tìm kiếm hoặc chuyển trang sẽ làm mất các bản nháp chưa lưu này. Bạn có muốn tiếp tục?',
            'games.auto_fix_confirm': 'Xác nhận tự động sửa đường dẫn game',
            'games.auto_fix_error': 'Lỗi khi sửa đường dẫn: ',
            'games.auto_fix_success': 'Đã sửa đường dẫn game thành công! Đang khởi động lại...',
            'games.unicode_error_msg': 'Đường dẫn thư mục hoặc file game có chứa ký tự tiếng Việt / Unicode có dấu, có thể khiến bộ dịch bị lỗi. Bạn có muốn tự động sửa tên thư mục sang không dấu không?',
            'toast.clear_cache_error_all': 'Lỗi khi xóa toàn bộ cache',
            'toast.clear_error': 'Lỗi khi xóa: ',
            'toast.clear_game_success': 'Đã xóa toàn bộ dữ liệu của game',
            'toast.folder_error': 'Lỗi mở thư mục dữ liệu',
            'toast.game_cleared': 'Đã xóa dữ liệu câu dịch của game',
            'toast.invalid_number': 'Vui lòng nhập số lượng hợp lệ.',

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

            // === PLUGINS & AI HUB ===
            "plugins.title": "Bộ Dịch & AI Hub",
            "plugins.subtitle": "Quản lý và kích hoạt các mô hình AI dịch thuật game",
            "plugins.google_desc": "Miễn phí, nhanh, không cần API key.",
            "plugins.installed": "Mặc định",
            "plugins.deepl": "DeepL API",
            "plugins.deepl_desc": "Chất lượng dịch cao từ DeepL. Cần nhập API key.",
            "plugins.ready": "Sẵn sàng",
            "plugins.deepl_placeholder": "Nhập DeepL API Key...",
            "plugins.gemini": "Google Gemini",
            "plugins.gemini_desc": "AI thế hệ mới siêu tốc từ Google. Có gói Free Tier cực lớn không cần thẻ tín dụng.",
            "plugins.deepseek": "DeepSeek (V3 / R1)",
            "plugins.deepseek_desc": "Hiểu ngữ cảnh Visual Novel & RPG, dịch xưng hô tự nhiên, chi phí siêu rẻ.",
            "plugins.openai": "OpenAI (ChatGPT)",
            "plugins.openai_desc": "Dịch vụ AI mạnh mẽ và ổn định nhất từ OpenAI (hỗ trợ GPT-4o-mini, GPT-4o).",
            "plugins.claude": "Anthropic Claude",
            "plugins.claude_desc": "Văn phong văn học sâu sắc, dịch lời thoại biểu cảm và tự nhiên nhất thế giới.",
            "plugins.kimi": "Kimi (Moonshot AI)",
            "plugins.kimi_desc": "Mô hình ngôn ngữ xử lý tiếng Trung, cổ phong và thành ngữ tối ưu nhất.",
            "plugins.custom_llm": "Custom / Local LLM",
            "plugins.custom_llm_desc": "Tự kết nối mô hình chạy cục bộ qua Ollama, LM Studio hoặc OpenRouter.",
            "plugins.api_key_label": "Khóa API (API Key):",
            "plugins.model_label": "Mô hình (Model):",
            "plugins.base_url_label": "Địa chỉ Base URL:",
            "plugins.get_free_key": "Lấy Key Miễn Phí",
            "plugins.test_btn": "Kiểm tra kết nối",
            "plugins.testing": "Đang kiểm tra...",
            "plugins.test_success": "Kết nối thành công ({ms}ms)!",
            "plugins.test_failed": "Lỗi kết nối: {error}",
            "plugins.key_saved": "Đã lưu cấu hình AI!",
            "plugins.key_configured": "Đã cấu hình",
            "plugins.key_not_configured": "Chưa nhập Key",
            "plugins.free_badge": "Free 100%",
            "plugins.recommended_badge": "Đề xuất",
            "plugins.fast_badge": "Siêu tốc",
            "plugins.api_key_placeholder": "Nhập API Key...",
            "plugins.model_placeholder": "Tên model (vd: qwen2.5:7b)...",
            "plugins.base_url_placeholder": "http://localhost:11434/v1",
            "plugins.clear_key": "Xóa Key",
            "plugins.custom_model_hint": "Nhập bất kỳ model ID nào (VD: deepseek-v4, claude-3-7-sonnet...)",
            "plugins.toggle_visibility": "Ẩn/Hiện khóa API",
            "plugins.libre_desc": "Mã nguồn mở, tự host được, hoàn toàn miễn phí.",
            "plugins.coming_soon": "Sắp có",
            "plugins.studio_title": "Universal AI Studio (Chuẩn Hoá Đa Mô Hình)",
            "plugins.studio_desc": "Cấu hình kết nối bất kỳ mô hình AI nào trên thế giới thông qua kiến trúc Adapter chuẩn hóa.",
            "plugins.provider_label": "Hãng Cung Cấp (Provider):",
            "plugins.save_btn": "Lưu Cấu Hình",
            "plugins.active_profiles": "Các AI Đã Cấu Hình Sẵn Sàng:",
            "plugins.warning_gemini_key": "Có vẻ đây là API Key của Google Gemini (AIzaSy...), không phải của {provider}!",
            "plugins.warning_claude_key": "Có vẻ đây là API Key của Anthropic Claude (sk-ant-...), không phải của {provider}!",
            "plugins.warning_deepl_key": "Có vẻ đây là API Key của DeepL Free (:fx), không phải của {provider}!",
            "plugins.warning_model_mismatch": "Mô hình '{model}' có vẻ là của {detected}, không phải của {provider}!",
            "plugins.warning_key_format": "Hình như API Key không đúng định dạng phổ biến của {provider}. Bạn hãy kiểm tra lại nhé.",
            "plugins.fetch_models_btn": "Đọc từ API",
            "plugins.fetch_models_hint": "Lấy danh sách mô hình từ tài khoản API của bạn",
            "plugins.fetch_models_loading": "Đang tải danh sách mô hình...",
            "plugins.fetch_models_success": "Đã tải {count} mô hình khả dụng từ tài khoản của bạn!",
            "plugins.fetch_models_empty": "Không tìm thấy mô hình nào từ tài khoản.",
            "plugins.suggest_model": "Gợi ý: Có phải bạn muốn chọn: ",
            "plugins.invalid_model_chars": "Tên mô hình không được chứa dấu cách hoặc dấu phẩy.",
            "error.tier_no_access": "Tài khoản hoặc API Key của bạn chưa được cấp quyền truy cập mô hình này: {error}",
            "error.model_missing": "Vui lòng chọn hoặc nhập tên Mô hình AI.",
            "error.base_url_missing": "Vui lòng nhập địa chỉ Base URL cho Custom / Local LLM.",
            "plugins.change_key": "Thay đổi Key",
            "plugins.cancel_change_key": "Hủy",
            "plugins.no_active_profiles": "Chưa có AI nào được cấu hình. Nhập API Key ở trên để kích hoạt.",
            "plugins.advanced_options": "Tùy chọn nâng cao (Base URL / Proxy)",
            "plugins.key_locked_desc": "Khóa API đã lưu an toàn",
            "plugins.key_locked_value": "••••••••••••••••••••••••••••••••",
            "plugins.clear_key_confirm": "Bạn có chắc chắn muốn xóa API Key và hủy cấu hình của {provider} không?",
            "plugins.clear_key_success": "Đã xóa API Key và hủy cấu hình của {provider} thành công.",
            "plugins.reset_model_btn": "Đặt lại mô hình mặc định",
            "plugins.reset_model_success": "Đã đặt lại mô hình mặc định ({model}) cho {provider}.",
            "plugins.operation_in_progress": "Đang có tác vụ xử lý (kiểm tra hoặc đọc API), vui lòng chờ trong giây lát!",
            "plugins.saving_in_progress": "Đang lưu cấu hình...",
            "plugins.clearing_in_progress": "Đang xóa cấu hình...",
            "plugins.remove_profile_tooltip": "Xóa cấu hình của hãng này",
            "games.engine_ready": "Sẵn sàng",
            "games.engine_no_key": "Chưa có Key",
            "games.engine_warning_tooltip": "Cần cấu hình API Key trong Cài đặt để sử dụng",
            "games.cannot_change_engine": "Không thể thay đổi bộ dịch khi đang dịch!",

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
            "toast.no_ai_key": "Lỗi: Bạn chưa cấu hình API Key cho {provider} trong mục Bổ trợ / AI Hub!",
            "toast.key_cleared": "Đã xóa API Key của {provider}!",
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
            "data.no_games": "Không có dữ liệu game nào.",
            "data.game_name": "Tên Game: ",
            "data.folder": "Thư mục: ",
            "data.entries_count": "Số câu: ",
            "data.terms_count": "Thuật ngữ: ",
            "data.size_display": "Kích thước (Size): ",
            "data.clear_game_confirm": "Bạn có chắc chắn muốn xóa TOÀN BỘ dữ liệu dịch và thuật ngữ của game này?",
            "data.keep_prompt": "Nhập số câu mới nhất muốn GIỮ LẠI (những câu cũ hơn sẽ bị xóa):",
            "data.clear_all_confirm": "Bạn có chắc chắn muốn xóa toàn bộ Cache?",
            "data.clear_tm_confirm": "Bạn có chắc chắn muốn xóa toàn bộ Translation Memory và thuật ngữ của tất cả các game?",


            // === MISC ===
            "error.engine_not_supported": "Lỗi: Hệ thống chưa hỗ trợ tự động dịch cho Engine này ({engine}). Vui lòng chọn game Unity, RPG Maker hoặc RenPy.",
            "hello.loading": "Khởi tạo hệ thống...",
            "goodbye.title": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
            "goodbye.subtitle": "Đang lưu cài đặt và tắt hệ thống...",
            "goodbye.message": "Cảm ơn bạn đã sử dụng ATM. Hẹn gặp lại!",
            "sidebar.pin_tooltip": "Ghim thanh bên",
            "sidebar.unpin_tooltip": "Bỏ ghim thanh bên",
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
            'translation.preparing': 'Preparing translation...',
            'translation.cancelled': 'Translation cancelled',
            'translation.success': 'Translation completed',
            'translation.failed': 'Translation failed',
            'translation.rate_limited': 'API rate limited (HTTP 429)',
            'translation.error': 'Error during translation',
            'translation.not_running': 'No translation is currently running',
            'translation.realtime_running': 'Real-time translation running...',
            'translation.realtime_finished': 'Game closed',
            'translation.ready': 'Ready',
            'common.lines': 'lines',
            'status.ready': 'Ready',
            'toast.game_busy': 'Previous translation is still shutting down, please wait a moment.',
            'workspace.coverage_title': '{engine} Coverage Report',
            'workspace.coverage_stats': 'Total: {total}\nTranslated: {translated}\nUntranslated: {untranslated}\nCoverage: {coverage}%',
            'workspace.audit_failed': 'Failed to audit {engine} coverage.',
            'workspace.job_already_running': 'Job is already running!',
            'workspace.extract_started': 'Extract job started.',
            'workspace.extract_completed': 'Extract job completed!',
            'workspace.extract_failed': 'Extract job {status}',
            'workspace.extract_start_error': 'Failed to start extract job.',
            'error.game_not_found': 'Game not found in the system!',
            'error.target_lang_missing': 'Please select target language before proceeding.',
            'toast.delete_running_error': 'Game is currently running or translating. Please stop it before deleting!',
            'toast.clear_running_error': 'Cannot clear data while translation is running. Stop it first!',
            'error.invalid_threshold': 'Translation-memory threshold must be between 0 and 1.',
            'error.cleanup_permission_denied': 'Cleanup failed (Permission Denied). Please run ATM as Administrator. Details: {details}',
            'error.api_unauthorized': 'Invalid or expired API Key (HTTP 401/403)!',
            'error.api_rate_limited': 'Rate limit exceeded (HTTP 429)! Please wait a few seconds.',
            'error.api_not_found': 'Model or API endpoint not found (HTTP 404)!',
            'error.api_key_missing': 'API Key is required. Please enter an API key before testing.',
            'error.api_connection_failed': 'Connection to AI failed: {error}',
            'error.api_empty_response': 'Empty response received from AI model.',
            'error.invalid_api_key_format': 'Invalid API Key format: {error}',
            'error.key_too_short_5': 'API Key is too short (minimum 5 characters)!',
            'error.key_too_short_deepl': 'DeepL API key is too short (minimum 20 characters)!',
            'error.key_too_short_general': 'API Key for {provider} is too short ({len} chars). Standard key is at least {min_len} chars!',
            'error.cannot_change_engine_while_translating': 'Cannot change translator while translation is in progress! Please stop first.',

            
            'editor.master_save': 'Save changes',
            'editor.master_cancel': 'Discard all',
            'editor.confirm_discard': 'You have unsaved changes. What would you like to do?',
            'editor.discard_leave': 'Discard & Leave',
            'editor.save_leave': 'Save & Leave',
            'editor.missing_vars': '⚠️ Warning: Missing vars {vars}',
            'editor.saving': 'Saving...',
            'editor.qa_running': 'Running QA...',
            'editor.qa_found': 'Found {count} QA issue(s)!',
            'editor.qa_clean': 'Great! No QA issues found.',
            'editor.qa_error': 'Error running QA scan',
            'editor.qa_no_entries': 'No translation lines available for QA scanning!',
            'editor.qa_no_translations': 'No translated lines found yet. Please translate before running QA!',
            'editor.apply_success': 'Applied suggestion',
            'editor.apply_error': 'Error saving suggestion',
            'editor.empty': 'No data available.',
            'editor.save_error': 'Could not save translation. Restored original.',
            'editor.batch_save_partial': 'Saved {saved}. Failed/conflicts: {failed}. Please retry.',
            'editor.network_error': 'Network error or data conflict',
            'editor.error_load': 'Error loading data',
            'editor.keep_mine': 'Keep mine (Overwrite)',
            'editor.use_new': 'Use new version',

            'glossary.add_success': 'Term added successfully',
            'glossary.add_error': 'Error adding term',
            'glossary.export_success': 'CSV file downloaded successfully',
            'glossary.export_error': 'Error exporting Glossary',
            'glossary.import_confirm': 'Preview Import:\n- {new} New\n- {conflict} Conflicts\n- {duplicate} Duplicates\n- {invalid} Invalid.\n\nDo you want to Overwrite (Merge)?',
            'glossary.import_success': 'Glossary imported successfully',
            'glossary.import_error': 'Import Error',

            'toast.add_game_error': 'Error adding game',
            'toast.delete_success': 'Game deleted successfully',
            'toast.game_translating': 'Game is currently translating, cannot launch right now!',
            'card.start': 'Start translation',
            'card.stop': 'Stop',
            'card.resume': 'Resume (Error/Restart)',
            'card.play': 'Play Game',
            'card.play_now': 'Play Game Now',
            'card.play_tooltip': 'Play Game (Direct)',
            'card.play_disabled_translating': 'Game is currently translating, cannot launch',
            'card.retranslate': 'Re-translate',
            'games.btn_sync': 'Sync & Translate',
            'games.needs_sync_tooltip': 'New changes detected from Editor/Glossary. Click to sync and apply.',
            'card.delete_confirm': 'Are you sure you want to delete this game? (The game folder will be reverted to original)',
            'card.delete_purge_data': 'Permanently delete translation data (Frees ~{size}MB Database). If unchecked, data is kept for future restoration.',
            'games.btn_select': 'Select',
            'games.btn_select_all': 'Select All',
            'games.btn_deselect_all': 'Deselect All',
            'games.btn_delete_selected': 'Delete ({count})',
            'games.btn_cancel_select': 'Cancel',
            'games.delete_multiple_confirm': 'Are you sure you want to delete {count} selected games? (Game files will be reverted to original)',
            'games.delete_multiple_success': 'Successfully deleted {count} games',
            'games.no_game_selected': 'Please select at least one game',
            'app.offline': 'Disconnected from server',
            'editor.conflict_msg': 'Data on server has changed. Do you want to overwrite?',
            'editor.search_draft_warning': 'You have unsaved changes. Searching or paging will discard these drafts. Continue?',
            'games.auto_fix_confirm': 'Confirm auto-fix game path',
            'games.auto_fix_error': 'Error fixing path: ',
            'games.auto_fix_success': 'Game path fixed successfully! Restarting...',
            'games.unicode_error_msg': 'Game path contains non-ASCII or accented characters which may cause translation engine errors. Do you want to automatically rename folder to ASCII?',
            'toast.clear_cache_error_all': 'Error clearing all cache',
            'toast.clear_error': 'Clear error: ',
            'toast.clear_game_success': 'Game data cleared successfully',
            'toast.folder_error': 'Error opening folder',
            'toast.game_cleared': 'Game data cleared successfully.',
            'toast.invalid_number': 'Please enter a valid number.',
            'data.loading': 'Loading data...',
            'plugins.deepl_configured': 'Configured',

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
            'workspace.default_title': 'Workspace',
            'workspace.default_subtitle': 'Loading...',

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

            // === PLUGINS & AI HUB ===
            "plugins.title": "Translation Engines & AI Hub",
            "plugins.subtitle": "Manage and activate AI translation engines for your games",
            "plugins.google_desc": "Free, fast, no API key required.",
            "plugins.installed": "Default",
            "plugins.deepl": "DeepL API",
            "plugins.deepl_desc": "High quality translation from DeepL. API key required.",
            "plugins.ready": "Ready",
            "plugins.deepl_placeholder": "Enter DeepL API Key...",
            "plugins.gemini": "Google Gemini",
            "plugins.gemini_desc": "Ultra-fast multimodal AI from Google with generous Free Tier (no credit card required).",
            "plugins.deepseek": "DeepSeek (V3 / R1)",
            "plugins.deepseek_desc": "Understands Visual Novel & RPG nuances, natural character pronouns, ultra-low cost.",
            "plugins.openai": "OpenAI (ChatGPT)",
            "plugins.openai_desc": "High-performance and rock-solid reliability by OpenAI (supports GPT-4o-mini, GPT-4o).",
            "plugins.claude": "Anthropic Claude",
            "plugins.claude_desc": "Literary, emotionally expressive dialogues with top-tier nuance and style.",
            "plugins.kimi": "Kimi (Moonshot AI)",
            "plugins.kimi_desc": "Specialized in Chinese text, wuxia lore, and JRPG idioms.",
            "plugins.custom_llm": "Custom / Local LLM",
            "plugins.custom_llm_desc": "Run local models offline via Ollama, LM Studio, or connect to OpenRouter.",
            "plugins.api_key_label": "API Key:",
            "plugins.model_label": "Model:",
            "plugins.base_url_label": "Endpoint / Base URL:",
            "plugins.get_free_key": "Get Free Key",
            "plugins.test_btn": "Test Connection",
            "plugins.testing": "Testing...",
            "plugins.test_success": "Connection successful ({ms}ms)!",
            "plugins.test_failed": "Connection failed: {error}",
            "plugins.key_saved": "AI Configuration Saved!",
            "plugins.key_configured": "Configured",
            "plugins.key_not_configured": "Key Not Set",
            "plugins.free_badge": "Free 100%",
            "plugins.recommended_badge": "Recommended",
            "plugins.fast_badge": "Ultra Fast",
            "plugins.api_key_placeholder": "Enter API Key...",
            "plugins.model_placeholder": "Model name (e.g. qwen2.5:7b)...",
            "plugins.base_url_placeholder": "http://localhost:11434/v1",
            "plugins.clear_key": "Clear Key",
            "plugins.custom_model_hint": "Enter any model ID (e.g. deepseek-v4, claude-3-7-sonnet...)",
            "plugins.toggle_visibility": "Toggle API Key visibility",
            "plugins.libre_desc": "Open source, self-hosted, completely free.",
            "plugins.coming_soon": "Coming Soon",
            "plugins.studio_title": "Universal AI Studio (Multi-Model Standardization)",
            "plugins.studio_desc": "Configure and connect any AI model worldwide through standardized Adapter architecture.",
            "plugins.provider_label": "Provider:",
            "plugins.save_btn": "Save Configuration",
            "plugins.active_profiles": "Configured Ready AI Providers:",
            "plugins.warning_gemini_key": "This looks like a Google Gemini API Key (AIzaSy...), not for {provider}!",
            "plugins.warning_claude_key": "This looks like an Anthropic Claude API Key (sk-ant-...), not for {provider}!",
            "plugins.warning_deepl_key": "This looks like a DeepL Free API Key (:fx), not for {provider}!",
            "plugins.warning_model_mismatch": "Model '{model}' appears to belong to {detected}, not {provider}!",
            "plugins.warning_key_format": "This doesn't seem to match the typical API Key format for {provider}. Please verify.",
            "plugins.fetch_models_btn": "Fetch from API",
            "plugins.fetch_models_hint": "Fetch accessible models directly from your API account",
            "plugins.fetch_models_loading": "Fetching available models...",
            "plugins.fetch_models_success": "Loaded {count} available models from your account!",
            "plugins.fetch_models_empty": "No models found from this account.",
            "plugins.suggest_model": "Did you mean: ",
            "plugins.invalid_model_chars": "Model name cannot contain spaces or commas.",
            "error.tier_no_access": "Your account/API Key does not have permission for this model: {error}",
            "error.model_missing": "Please select or enter an AI Model name.",
            "error.base_url_missing": "Base URL is required for Custom / Local LLM.",
            "plugins.change_key": "Change Key",
            "plugins.cancel_change_key": "Cancel",
            "plugins.no_active_profiles": "No AI profiles configured yet. Enter an API Key above to activate.",
            "plugins.advanced_options": "Advanced Options (Base URL / Proxy)",
            "plugins.key_locked_desc": "API Key securely configured",
            "plugins.key_locked_value": "••••••••••••••••••••••••••••••••",
            "plugins.clear_key_confirm": "Are you sure you want to remove the API Key and configuration for {provider}?",
            "plugins.clear_key_success": "API Key and configuration for {provider} removed successfully.",
            "plugins.reset_model_btn": "Reset default model",
            "plugins.reset_model_success": "Reset to default model ({model}) for {provider}.",
            "plugins.operation_in_progress": "An operation is currently in progress (testing connection or fetching API), please wait!",
            "plugins.saving_in_progress": "Saving configuration...",
            "plugins.clearing_in_progress": "Clearing configuration...",
            "plugins.remove_profile_tooltip": "Remove configuration for this provider",
            "games.engine_ready": "Ready",
            "games.engine_no_key": "Key Required",
            "games.engine_warning_tooltip": "API Key configuration required in Settings",
            "games.cannot_change_engine": "Cannot change translator while translation is in progress!",

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
            "toast.no_ai_key": "Error: API Key for {provider} not configured in AI Hub!",
            "toast.key_cleared": "API Key for {provider} cleared!",
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
            "data.no_games": "No game data found.",
            "data.game_name": "Game Name: ",
            "data.folder": "Folder: ",
            "data.entries_count": "Lines: ",
            "data.terms_count": "Glossary: ",
            "data.size_display": "Size: ",
            "data.clear_game_confirm": "Are you sure you want to clear ALL translation data and glossary for this game?",
            "data.keep_prompt": "Enter the number of latest entries to KEEP (older ones will be deleted):",
            "data.clear_all_confirm": "Are you sure you want to clear all Cache?",
            "data.clear_tm_confirm": "Are you sure you want to clear all Translation Memory and glossaries?",



            // === MISC ===
            "error.engine_not_supported": "Error: Real-time translation is not supported for this Engine ({engine}). Please select a Unity, RPG Maker or RenPy game.",
            "hello.loading": "Initializing system...",
            "goodbye.title": "Thank you for using ATM. See you again!",
            "goodbye.subtitle": "Saving settings and shutting down...",
            "goodbye.message": "Thank you for using ATM. See you again!",
            "sidebar.pin_tooltip": "Pin sidebar",
            "sidebar.unpin_tooltip": "Unpin sidebar",
        }
    };

    let currentLang = window.ATM.store.get('atm_lang') || 'vi';

    window.ATM.i18n = {
        /**
         * Lấy câu dịch theo key
         */
        t: function(key, fallbackOrParams = {}) {
            let text = dict[currentLang] && dict[currentLang][key];
            if (text === undefined) {
                if (typeof fallbackOrParams === 'string') return fallbackOrParams;
                let enText = dict['en'] && dict['en'][key];
                if (enText !== undefined) return enText;
                return key;
            }
            if (typeof fallbackOrParams === 'object') {
                for (const [k, v] of Object.entries(fallbackOrParams)) {
                    text = text.replace(new RegExp(`{${k}}`, 'g'), v);
                }
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
                if (window.ATM.events) {
                    window.ATM.events.publish('lang:changed', lang);
                }
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
