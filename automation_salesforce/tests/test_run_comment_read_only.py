import io
import unittest
from contextlib import redirect_stdout

from run_comment_read_only import print_comment_summary


class CommentSummaryTests(unittest.TestCase):
    def test_summary_excludes_the_comment_content(self):
        output = io.StringIO()

        with redirect_stdout(output):
            print_comment_summary(
                lead_id="00Q000000000001AAA",
                field_found=True,
                comment_length=31,
                next_int=2,
            )

        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "Lead ID: 00Q000000000001AAA",
                "Campo 'Otra información' encontrado: sí",
                "Cantidad de caracteres: 31",
                "Próximo INT: 2",
            ],
        )
        self.assertNotIn("Envío WhatsApp", output.getvalue())


if __name__ == "__main__":
    unittest.main()
