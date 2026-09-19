import unittest
import os
import re

class TestWorkspaceTabs(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.html_path = os.path.join(self.base_dir, "atm", "ui", "web", "index.html")
        self.workspace_js_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "features", "workspace.js")
        self.glossary_js_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "features", "glossary.js")
        self.tm_js_path = os.path.join(self.base_dir, "atm", "ui", "web", "js", "features", "tm.js")

    def test_templates_exist_in_index_html(self):
        with open(self.html_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('id="workspace-glossary-template"', content)
        self.assertIn('id="workspace-tm-template"', content)
        self.assertIn('id="glossary-source"', content)
        self.assertIn('id="glossary-target"', content)
        self.assertIn('id="glossary-list"', content)
        self.assertIn('id="tm-source-text"', content)
        self.assertIn('id="tm-suggestions"', content)

    def test_workspace_js_wires_tabs_and_purges_polling(self):
        with open(self.workspace_js_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Zombie polling check
        self.assertNotIn("window.ATM.polling", content)

        # Tab in-place wiring
        self.assertIn("startGlossary", content)
        self.assertIn("startTM", content)
        self.assertIn("startGlossary(game.id)", content)
        self.assertIn("startTM(game.id)", content)
        self.assertIn("workspace-glossary-template", content)
        self.assertIn("workspace-tm-template", content)

        # Safe error message extraction
        self.assertIn("e.error || e.message", content)

    def test_glossary_and_tm_modules_export_mount(self):
        with open(self.glossary_js_path, "r", encoding="utf-8") as f:
            glossary_content = f.read()
        with open(self.tm_js_path, "r", encoding="utf-8") as f:
            tm_content = f.read()

        # Exports mount
        self.assertRegex(glossary_content, r"return\s*\{[^}]*mount[^}]*\};")
        self.assertRegex(tm_content, r"mount:\s*\(gameId\)\s*=>")

        # Outline button styling with SVG (no hardcoded background styles)
        self.assertIn("btn-icon btn-delete", glossary_content)
        self.assertNotIn("var(--danger-color, #ef4444)", glossary_content)
        self.assertIn("<polyline points=\"3 6 5 6 21 6\"></polyline>", glossary_content)

        # Delegated event listener on document.body for dynamic templates
        self.assertIn("e.target.id === 'glossary-source'", glossary_content)
        self.assertIn("e.target.id === 'glossary-import-file'", glossary_content)
        self.assertIn("e.target.id === 'tm-source-text'", tm_content)

if __name__ == '__main__':
    unittest.main()
