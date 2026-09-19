import unittest
from pathlib import Path
import tempfile
import json
from atm.core.translation.rpgmaker_translator import RPGMakerTranslator

class TestRPGMakerSystemOverlay(unittest.TestCase):
    def setUp(self):
        self.translator = RPGMakerTranslator()

    def test_install_overlay_plugin_inserts_at_index_zero(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            js_dir = tmp_path / "www" / "js"
            plugins_dir = js_dir / "plugins"
            plugins_dir.mkdir(parents=True)
            data_dir = tmp_path / "www" / "data"
            data_dir.mkdir(parents=True)

            # Pre-existing plugins.js with Yanfly and custom plugins
            plugins_js = js_dir / "plugins.js"
            initial_plugins = [
                {"name": "Yanfly_CoreEngine", "status": True, "description": "Core", "parameters": {}},
                {"name": "YEP_MessageCore", "status": True, "description": "Message", "parameters": {}}
            ]
            plugins_js.write_text(f"var $plugins = {json.dumps(initial_plugins, indent=2)};\n", encoding="utf-8-sig")

            # Run install
            self.translator._install_overlay_plugin(tmp_path / "www", data_dir)

            # Read back plugins.js
            content = plugins_js.read_text(encoding="utf-8-sig")
            self.assertIn("ATM_Overlay", content)
            
            # Parse json array from content
            import re
            match = re.search(r'var\s+\$plugins\s*=\s*(\[.*\])\s*;', content, re.DOTALL)
            self.assertIsNotNone(match)
            loaded_arr = json.loads(match.group(1))
            
            # Verify ATM_Overlay is at index 0!
            self.assertEqual(loaded_arr[0]["name"], "ATM_Overlay")
            self.assertEqual(loaded_arr[1]["name"], "Yanfly_CoreEngine")
            self.assertEqual(loaded_arr[2]["name"], "YEP_MessageCore")

    def test_overlay_plugin_source_contains_data_patching_logic(self):
        src = self.translator._overlay_plugin_source(Path("C:/fake/data"))
        
        # Check in-memory patchDataObjects logic
        self.assertIn("ATMOverlay.patchDataObjects", src)
        self.assertIn("DataManager.onLoad", src)
        self.assertIn("$dataSystem", src)
        self.assertIn("$dataMapInfos", src)
        
        # Check system term groups
        self.assertIn("['basic', 'commands', 'params', 'messages']", src)
        self.assertIn("['elements', 'skillTypes', 'weaponTypes', 'armorTypes', 'equipTypes']", src)
        self.assertIn("gameTitle", src)
        self.assertIn("currencyUnit", src)

    def test_overlay_plugin_js_syntax_balance(self):
        src = self.translator._overlay_plugin_source(Path("C:/fake/data"))
        
        # Verify brace balance in the generated JS
        open_braces = src.count("{")
        close_braces = src.count("}")
        self.assertEqual(open_braces, close_braces, f"Braces mismatch: {open_braces} open vs {close_braces} close")
        
        open_parens = src.count("(")
        close_parens = src.count(")")
        self.assertEqual(open_parens, close_parens, f"Parens mismatch: {open_parens} open vs {close_parens} close")

if __name__ == '__main__':
    unittest.main()
