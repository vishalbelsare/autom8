from collections import namedtuple
from contextlib import contextmanager
import logging
import random

import numpy as np
import scipy.sparse
import sklearn.preprocessing

from .evaluate import evaluate_pipeline
from .exceptions import expected, typename
from .inference import _infer_role
from .matrix import create_matrix
from .pipeline import Pipeline
from .receiver import Receiver


def create_training_context(
    dataset,
    target_column=None,
    problem_type=None,
    test_ratio=None,
    receiver=None,
):
    # Create a default receiver if the user didn't provide one.
    if receiver is None:
        receiver = Receiver()

    matrix = create_matrix(dataset, receiver)
    num_cols = len(matrix.columns)

    if num_cols == 0:
        raise expected('dataset with more than one column', repr(dataset))

    if num_cols == 1:
        raise expected('dataset with more than one column', num_cols)

    if target_column is None:
        target_column = num_cols - 1

    if not isinstance(target_column, (int, str)):
        raise expected(f'target_column to be an int or a str',
            typename(target_column))

    if isinstance(target_column, str):
        target_column = target_column.strip()
        for index, col in enumerate(matrix.columns):
            if target_column == col.name.strip():
                target_column = index
                break

    if isinstance(target_column, str):
        colnames = {col.name for col in matrix.columns}
        raise expected('target_column to be one of: {colnames}',
            repr(target_column))

    if isinstance(target_column, int) and target_column >= len(matrix.columns):
        raise expected(
            f'target_column to be valid column number (less than {num_cols})',
            target_column,
        )

    labelcol = matrix.columns[target_column]
    label_name, label_values = labelcol.name, labelcol.values
    matrix.drop_columns_by_index(target_column)

    if problem_type is None:
        role = _infer_role(labelcol, receiver)
        problem_type = 'regression' if role == 'numerical' else 'classification'

    valid_problems = {'regression', 'classification'}
    if not isinstance(problem_type, str) or problem_type not in valid_problems:
        raise expected(f'problem_type in {valid_problems}', repr(problem_type))

    if problem_type == 'regression':
        labels = LabelContext(label_name, label_values, label_values, None)
    else:
        assert problem_type == 'classification'
        encoder = sklearn.preprocessing.LabelEncoder()
        encoded = encoder.fit_transform(label_values)
        labels = LabelContext(label_name, label_values, encoded, encoder)

    if test_ratio is None:
        test_ratio = 0.2

    if not isinstance(test_ratio, float) or not (0 < test_ratio < 1):
        raise expected('test_ratio between 0.0 and 1.0', test_ratio)

    count = len(matrix)
    test_indices = sorted(random.sample(range(count), int(count * test_ratio) or 1))
    return TrainingContext(matrix, labels, test_indices, problem_type, receiver)


class TrainingContext:
    def __init__(
            self, matrix, labels, test_indices,
            problem_type, receiver, steps=None
        ):
        self.matrix = matrix.copy()
        self.labels = labels
        self.test_indices = test_indices
        self.problem_type = problem_type
        self.receiver = receiver
        self.steps = list(steps) if steps else []
        self.pool = None

    def copy(self):
        return TrainingContext(
            matrix=self.matrix,
            labels=self.labels,
            test_indices=self.test_indices,
            problem_type=self.problem_type,
            receiver=self.receiver,
            steps=self.steps,
        )

    @property
    def is_training(self):
        return True

    @property
    def is_classification(self):
        return self.problem_type == 'classification'

    @property
    def is_regression(self):
        return self.problem_type == 'regression'

    def __lshift__(self, estimator):
        if self.pool is None:
            self.fit(estimator)
        elif hasattr(self.pool, 'fit'):
            self.pool.fit(self, estimator)
        else:
            self.pool.submit(self.fit, estimator)

    def fit(self, estimator):
        X, y = self.training_data()

        # Force all the columns to be floats at this point.
        if X.dtype != float:
            X = X.astype(float)

        try:
            X = scipy.sparse.csr_matrix(X)
            estimator.fit(X, y)
        except Exception:
            logging.getLogger('autom8').exception('Training failed')
            return

        pipeline = Pipeline(list(self.steps), estimator, self.labels.encoder)
        report = evaluate_pipeline(self, pipeline)
        self.receiver.receive_pipeline(pipeline, report)

    def submit(self, func, *args, **kwargs):
        if self.pool is None:
            func(*args, **kwargs)
        else:
            self.pool.submit(f, *args, **kwargs)

    def testing_data(self):
        feat = self.matrix.select_rows(self.test_indices)
        lab = self.labels.encoded[self.test_indices]
        return (feat.stack_columns(), lab)

    def training_data(self):
        feat = self.matrix.exclude_rows(self.test_indices)
        lab = np.delete(self.labels.encoded, self.test_indices)
        return (feat.stack_columns(), lab)

    @contextmanager
    def sandbox(self):
        saved_matrix = self.matrix.copy()
        saved_steps = list(self.steps)
        yield
        self.matrix = saved_matrix
        self.steps = saved_steps

    @contextmanager
    def parallel(self):
        if self.pool is not None:
            yield
            return

        num_steps = len(self.steps)
        self.pool = self.receiver.create_executor()
        yield

        try:
            self.pool.shutdown(wait=True)
        finally:
            self.pool = None

        if len(self.steps) != num_steps:
            self.receiver.warn(
                'Potential race condition: The TrainingContext was updated'
                ' within a `parallel` context. To avoid any race conditions,'
                ' create a copy of the TrainingContext before applying any'
                ' preprocessing functions to it.'
            )


class LabelContext(namedtuple('LabelContext', 'name, original, encoded, encoder')):
    def decode(self, encoded_labels):
        if self.encoder is None:
            return encoded_labels
        else:
            return self.encoder.inverse_transform(encoded_labels)
