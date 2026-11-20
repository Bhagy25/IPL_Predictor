import numpy as np
import pandas as pd

from cricketlens.model_benchmark import TASKS, event_probabilities, score


def test_batter_probability_roundoff_at_one_is_valid_for_brier():
    task = TASKS[1]
    data = pd.DataFrame({task.target: [0, 1, 2]})
    predictions = np.array([[0.9, 0.08, 0.02], [0.0, 0.75, np.nextafter(0.25, 1) + 2e-15],
                            [0.1, 0.2, 0.7]])

    _, _, p30 = event_probabilities(task, data[task.target].to_numpy(), predictions)[0]
    assert p30[1] == 1.0
    assert np.isfinite(score(task, data, predictions)["brier"])
