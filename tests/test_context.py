import unittest
import numpy as np
from context import autom8


class TestAbstractContext(unittest.TestCase):
    def test_is_training_property(self):
        report = autom8.create_matrix([[1]])
        c1 = autom8.TrainingContext(report.matrix, None, None)
        c2 = autom8.PredictingContext(report.matrix)
        self.assertTrue(c1.is_training)
        self.assertFalse(c2.is_training)
        self.assertFalse(c1.is_predicting)
        self.assertTrue(c2.is_predicting)

    def test_require_training_context(self):
        report = autom8.create_matrix([[1]])
        c1 = autom8.TrainingContext(report.matrix, None, None)
        c2 = autom8.PredictingContext(report.matrix)

        # This should not raise an exception.
        c1.require_training_context()

        # But this should raise one.
        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*TrainingContext'):
            c2.require_training_context()


class TestTrainingContext(unittest.TestCase):
    def test_training_and_testing_data(self):
        report = autom8.create_matrix([
            [1, 5, True, 9],
            [2, 6, False, 10],
            [3, 7, False, 11],
            [4, 8, True, 12],
        ])
        labels = np.array([10, 20, 30, 40])
        ctx = autom8.TrainingContext(report.matrix, labels, [1, 3])
        m1, a1 = ctx.testing_data()
        m2, a2 = ctx.training_data()
        self.assertTrue(np.array_equal(a1, [20, 40]))
        self.assertTrue(np.array_equal(a2, [10, 30]))
        self.assertTrue(np.array_equal(m1, [
            [2, 6, False, 10],
            [4, 8, True, 12],
        ]))
        self.assertTrue(np.array_equal(m2, [
            [1, 5, True, 9],
            [3, 7, False, 11],
        ]))
