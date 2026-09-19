import os
import unittest

class TestDeleteButtonStyling(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.css_path = os.path.join(self.base_dir, "atm", "ui", "web", "styles.css")
        self.html_path = os.path.join(self.base_dir, "atm", "ui", "web", "index.html")

    def test_btn_delete_is_outline_button(self):
        with open(self.css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # .btn-delete should have outline background and red text/border, not solid background
        self.assertIn(".btn-delete {", css)
        self.assertIn("background: var(--btn-outline-bg, #ffffff);", css)
        self.assertIn("color: var(--danger, #ef4444);", css)
        self.assertIn("border: 1.5px solid var(--danger, #ef4444);", css)

    def test_btn_icon_btn_delete_hover_does_not_use_accent_color(self):
        with open(self.css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # .btn-icon.btn-delete must have outline base and dedicated red hover
        self.assertIn(".btn-icon.btn-delete {", css)
        self.assertIn(".btn-icon.btn-delete:hover {", css)
        self.assertIn("background: var(--danger, #ef4444);", css)

        hover_idx = css.find(".btn-icon.btn-delete:hover")
        hover_block = css[hover_idx:css.find("}", hover_idx)]
        self.assertIn("var(--danger", hover_block)
        self.assertNotIn("var(--accent)", hover_block)

    def test_card_delete_button_has_btn_icon_class_and_modern_svg(self):
        with open(self.html_path, "r", encoding="utf-8") as f:
            html = f.read()

        self.assertIn('class="btn-icon btn-delete"', html)
        # Modern trash-2 icon with internal vertical slats (lines x1="10" and x1="14")
        self.assertIn('line x1="10" y1="11" x2="10" y2="17"', html)
        self.assertIn('line x1="14" y1="11" x2="14" y2="17"', html)

if __name__ == '__main__':
    unittest.main()
