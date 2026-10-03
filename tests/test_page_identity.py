from __future__ import annotations

import unittest

from page_identity import body, decorate_html, favicon_link, verify_decorated_html


class PageIdentityTests(unittest.TestCase):
    def test_each_page_identity_uses_a_distinct_embedded_svg(self):
        links = [
            favicon_link(identity)
            for identity in ("business-flow", "architecture", "productivity")
        ]
        self.assertEqual(len(links), len(set(links)))
        for identity, link in zip(
            ("business-flow", "architecture", "productivity"), links, strict=True
        ):
            self.assertIn(f'data-favicon="{identity}"', link)
            self.assertIn('type="image/svg+xml"', link)
            self.assertIn('href="data:image/svg+xml,', link)
            self.assertNotIn("http://", link)
            self.assertNotIn("https://", link)

    def test_decoration_only_changes_the_head(self):
        source = "<html><head><title>Prueba</title></head><body>Contenido</body></html>"
        published = decorate_html(source, "business-flow")
        verify_decorated_html(source, published, "business-flow")
        self.assertEqual(body(source), body(published))

    def test_rejects_existing_favicon_or_body_mutation(self):
        source = "<html><head><title>Prueba</title></head><body>Contenido</body></html>"
        published = decorate_html(source, "architecture")
        with self.assertRaisesRegex(ValueError, "ya declara"):
            decorate_html(published, "architecture")
        with self.assertRaisesRegex(ValueError, "cuerpo"):
            verify_decorated_html(
                source, published.replace("Contenido", "Alterado"), "architecture"
            )


if __name__ == "__main__":
    unittest.main()
