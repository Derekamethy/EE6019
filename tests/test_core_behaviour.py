import unittest

import numpy as np

from eeg_seizure_detection.evaluation import (
    compute_event_metrics,
    count_events,
    extract_binary_runs,
)
from eeg_seizure_detection.features import temporal_stack_features
from eeg_seizure_detection.preprocessing import apply_duration_constraint


class CoreBehaviourTests(unittest.TestCase):
    def test_duration_constraint_removes_short_runs(self):
        preds = np.array([0, 1, 1, 0, 1, 1, 1, 0], dtype=np.int8)
        cleaned = apply_duration_constraint(preds, min_epochs=3)
        np.testing.assert_array_equal(
            cleaned,
            np.array([0, 0, 0, 0, 1, 1, 1, 0], dtype=np.int8),
        )

    def test_temporal_stack_preserves_causal_history_order(self):
        x = np.array([[1, 10], [2, 20], [3, 30]], dtype=np.float32)
        y = np.array([0, 1, 0], dtype=np.int8)
        stacked, y_out = temporal_stack_features(x, y, history_epochs=1)
        expected = np.array(
            [[0, 0, 1, 10], [1, 10, 2, 20], [2, 20, 3, 30]],
            dtype=np.float32,
        )
        np.testing.assert_array_equal(stacked, expected)
        np.testing.assert_array_equal(y_out, y)

    def test_event_metrics_count_events_false_alarms_and_delay(self):
        y_true = np.array([0, 1, 1, 0, 0, 1, 1, 0], dtype=np.int8)
        y_pred = np.array([0, 0, 1, 0, 1, 1, 0, 0], dtype=np.int8)
        self.assertEqual(count_events(y_true), 2)
        starts, ends = extract_binary_runs(y_true)
        np.testing.assert_array_equal(starts, np.array([1, 5]))
        np.testing.assert_array_equal(ends, np.array([3, 7]))

        metrics = compute_event_metrics(y_true, y_pred, epoch_len_s=2)
        self.assertEqual(metrics["events"], 2.0)
        self.assertEqual(metrics["detected_events"], 2.0)
        self.assertEqual(metrics["sensitivity"], 1.0)
        self.assertEqual(metrics["false_alarm_events"], 1.0)
        self.assertAlmostEqual(metrics["mean_delay_s"], 1.0)
        self.assertAlmostEqual(metrics["median_delay_s"], 1.0)


if __name__ == "__main__":
    unittest.main()
