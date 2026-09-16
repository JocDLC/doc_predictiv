import unittest

from local_audit import mask_lead_id


class MaskLeadIdTests(unittest.TestCase):
    def test_masks_middle_of_standard_lead_id(self):
        self.assertEqual(mask_lead_id("00QbD00000t6sipUAA"), "00Qb...pUAA")

    def test_masks_short_value(self):
        self.assertEqual(mask_lead_id("1234"), "****")


if __name__ == "__main__":
    unittest.main()
