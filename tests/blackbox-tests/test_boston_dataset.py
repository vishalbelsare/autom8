import autom8
import datasets


def test_boston_dataset():
    acc = datasets.fit('boston.csv')

    # Assert that we at least got 10 reports.
    assert len(acc.reports) >= 10

    # Make sure each report has an r2_score.
    for report in acc.reports:
        s1 = report.train.metrics['r2_score']
        s2 = report.test.metrics['r2_score']
        assert s1 <= 1.0
        assert s2 <= 1.0
        assert isinstance(s1.tolist(), float)
        assert isinstance(s2.tolist(), float)

    # Assert that the best test score is better than 0.6.
    best = max(i.test.metrics['r2_score'] for i in acc.reports)
    assert best > 0.6

    # Make sure each pipeline can make predictions.
    vectors = [
        [
            'CRIM', 'ZN', 'INDUS', 'CHAS', 'NOX', 'RM', 'AGE',
            'DIS', 'RAD', 'TAX', 'PTRATIO', 'B', 'LSTAT',
        ],
        [0.007, 18, 2.3, 0, 0.5, 6.5, 65, 4, 1, 296, 15.4, 396.9, 4.98],
        [0.05, 0, 2.4, 0, 0.5, 7.8, 53, 3, 3, 193, 18, 392.63, 4.45],
    ]
    for report in acc.reports:
        tmp = autom8.Accumulator()
        pred = report.pipeline.run(vectors, receiver=tmp)
        assert len(pred.predictions) == 2
        assert isinstance(pred.predictions[0].tolist(), float)
        assert isinstance(pred.predictions[1].tolist(), float)
        assert not tmp.warnings
