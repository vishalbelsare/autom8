from pytest import approx
import numpy as np
import sklearn.linear_model
import autom8


def test_evaluate_pipeline():
    acc = autom8.Accumulator()
    inputs = [
        [1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [11, 12], [13, 14], [15, 16],
    ]
    dataset = [i + [i[0] + i[1]] for i in inputs]
    ctx = autom8.create_context(dataset, receiver=acc)

    # For now, just hack in the test_indices that we want.
    ctx.test_indices = [2, 5]

    autom8.add_column_of_ones(ctx)
    ctx << sklearn.linear_model.LinearRegression()
    assert len(acc.candidates) == 1

    candidate = acc.candidates[0]
    assert candidate.train.metrics['r2_score'] == 1.0
    assert candidate.test.metrics['r2_score'] == 1.0

    assert np.allclose(
        candidate.train.predictions,
        np.array([1+2, 3+4, 7+8, 9+10, 13+14, 15+16]),
    )

    assert np.allclose(
        candidate.test.predictions,
        np.array([5+6, 11+12]),
    )

    # Try using the pipeline to make some predictions.
    result = candidate.pipeline.run([[17, 18], [19, 20], [21, 22]], receiver=acc)

    assert np.allclose(result.predictions, np.array([17+18, 19+20, 21+22]))
    assert result.probabilities is None
    assert not acc.warnings
