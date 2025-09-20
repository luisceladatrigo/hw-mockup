import unittest

import core


class SmokeTests(unittest.TestCase):
    def test_version(self):
        self.assertRegex(core.__version__, r"^\d+\.\d+\.\d+")

    def test_sanitize(self):
        self.assertEqual(core.sanitize_plate(" abc-123 "), "ABC-123")
        self.assertEqual(core.sanitize_plate("a"), "")

    def test_assigner_minimal(self):
        a = core.LockerAssigner()
        idx, created = a.assign("ABC-123")
        self.assertTrue(created)
        self.assertEqual(idx, a.lookup("ABC-123"))
        self.assertTrue(a.release("ABC-123"))
        self.assertIsNone(a.lookup("ABC-123"))


if __name__ == "__main__":
    unittest.main()

