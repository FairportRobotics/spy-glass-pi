import json
import unittest

from spyglass.networktables import target_values
from spyglass.targets import Target


class NetworkTablesValuesTests(unittest.TestCase):
    def test_centered_target_has_zero_angle(self):
        values = target_values(
            [Target("red_robot", 0.9, 40, 30, 20, 20)], 100, 80, 60, 50
        )
        self.assertEqual(values["tv"], 1)
        self.assertAlmostEqual(values["tx"], 0)
        self.assertAlmostEqual(values["ty"], 0)
        self.assertEqual(values["target_class"], "red_robot")
        self.assertEqual(values["target_confidence"], 0.9)

    def test_best_target_and_all_targets_are_published(self):
        targets = [
            Target("red_robot", 0.7, 0, 0, 10, 10),
            Target("coral", 0.95, 40, 30, 20, 20),
        ]
        values = target_values(targets, 100, 80, 60, 50)
        self.assertEqual(values["target_count"], 2)
        self.assertEqual(values["target_class"], "coral")
        self.assertEqual(json.loads(values["targets"])[0]["label"], "red_robot")

    def test_no_targets_clear_limelight_values(self):
        values = target_values([], 100, 80, 60, 50)
        self.assertEqual((values["tv"], values["tx"], values["ty"], values["ta"]), (0, 0, 0, 0))
        self.assertEqual(values["targets"], "[]")


if __name__ == "__main__":
    unittest.main()
