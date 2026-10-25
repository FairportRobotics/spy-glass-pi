import unittest

from spyglass.targets import Target, suppress_overlapping_targets


class NonMaxSuppressionTests(unittest.TestCase):
    def test_suppresses_overlapping_boxes_of_the_same_class(self):
        targets = [
            Target("red_robot", 0.9, 0, 0, 20, 20),
            Target("red_robot", 0.8, 2, 2, 20, 20),
        ]
        self.assertEqual(
            suppress_overlapping_targets(targets, 0.5),
            [targets[0]],
        )

    def test_keeps_different_classes_even_when_boxes_overlap(self):
        targets = [
            Target("red_robot", 0.9, 0, 0, 20, 20),
            Target("coral", 0.8, 2, 2, 20, 20),
        ]
        self.assertEqual(
            suppress_overlapping_targets(targets, 0.5),
            targets,
        )

    def test_threshold_allows_less_overlapping_boxes(self):
        targets = [
            Target("coral", 0.9, 0, 0, 10, 10),
            Target("coral", 0.8, 8, 8, 10, 10),
        ]
        self.assertEqual(
            suppress_overlapping_targets(targets, 0.1),
            targets,
        )


if __name__ == "__main__":
    unittest.main()
