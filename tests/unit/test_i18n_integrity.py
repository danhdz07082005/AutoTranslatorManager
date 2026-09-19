import unittest
import re
import os

class TestI18nIntegrity(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.html_path = os.path.join(self.base_dir, "atm", "ui", "web", "index.html")
        self.i18n_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "core", "i18n.js")
        self.games_js_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "features", "games.js")

    def test_games_js_no_vietnamese_string_matching(self):
        with open(self.games_js_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn('includes("thêm vào hệ thống")', content)
        self.assertNotIn("includes('thêm vào hệ thống')", content)

    def test_html_critical_elements_have_i18n_attributes(self):
        with open(self.html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # #save-confirm-message must have data-i18n
        self.assertTrue('id="save-confirm-message"' in content and 'data-i18n="editor.confirm_discard"' in content)

        # #workspace-title must have data-i18n
        self.assertTrue('id="workspace-title"' in content and 'data-i18n="workspace.default_title"' in content)

        # #editor-master-save-btn and #editor-master-cancel-btn must have data-i18n-title
        self.assertTrue('id="editor-master-save-btn"' in content and 'data-i18n-title="editor.master_save"' in content)
        self.assertTrue('id="editor-master-cancel-btn"' in content and 'data-i18n-title="editor.master_cancel"' in content)

    def test_i18n_dictionary_contains_required_keys(self):
        with open(self.i18n_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_keys = [
            "editor.confirm_discard",
            "editor.master_save",
            "editor.master_cancel",
            "card.editor_tooltip",
            "card.delete_tooltip",
            "workspace.default_title",
            "workspace.default_subtitle",
            "toast.duplicate_game",
        ]

        for key in required_keys:
            # Check presence in both vi and en sections
            count = content.count(f"'{key}'") + content.count(f'"{key}"')
            self.assertGreaterEqual(count, 2, f"Key '{key}' must be defined in both vi and en in i18n.js")

if __name__ == '__main__':
    unittest.main()
