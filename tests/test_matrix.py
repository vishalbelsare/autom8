import unittest
import numpy as np
from context import autom8


class TestMatrix(unittest.TestCase):
    def test_invalid_arguments(self):
        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*list'):
            autom8.create_matrix(0)

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*list'):
            autom8.create_matrix('')

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*rows'):
            autom8.create_matrix({})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema'):
            autom8.create_matrix({'rows': []})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*rows'):
            autom8.create_matrix({'schema': []})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*rows'):
            autom8.create_matrix({'metadata': None})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema.*dict'):
            autom8.create_matrix({'rows': [[1]], 'schema': ['']})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema.*name'):
            autom8.create_matrix({'rows': [[1]], 'schema': [{}]})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema.*role'):
            autom8.create_matrix({'rows': [[1]], 'schema': [{}]})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema.*name'):
            autom8.create_matrix({'rows': [[1]], 'schema': [{'role': None}]})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*schema.*role'):
            autom8.create_matrix({'rows': [[1]], 'schema': [{'name': 'count'}]})

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*list'):
            autom8.create_matrix({
                'rows': 'hi',
                'schema': [{'name': 'msg', 'role': 'textual'}],
            })

        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*role in'):
            autom8.create_matrix({
                'rows': [['hi']],
                'schema': [{'name': 'msg', 'role': 'str'}],
            })

    def test_empty_datasets(self):
        for data in [[], (), {'rows': [], 'schema': []}]:
            report = autom8.create_matrix(data)
            self.assertEqual(report.matrix.columns, [])
            self.assertEqual(report.warnings, [])

    def test_empty_dataset_with_empty_rows(self):
        # Assert that we see one warning when we have three empty rows.
        report = autom8.create_matrix([[], [], []])
        self.assertEqual(report.matrix.columns, [])
        self.assertEqual(len(report.warnings), 1)

    def test_empty_dataset_warning_message(self):
        r1 = autom8.create_matrix([[]])
        r2 = autom8.create_matrix([[], []])
        r3 = autom8.create_matrix([[], [], []])
        self.assertEqual(r1.warnings, ['Dropped 1 empty row from dataset.'])
        self.assertEqual(r2.warnings, ['Dropped 2 empty rows from dataset.'])
        self.assertEqual(r3.warnings, ['Dropped 3 empty rows from dataset.'])

    def test_extra_columns_warning_message(self):
        r1 = autom8.create_matrix([[1, 2], [1, 2, 3]])
        r2 = autom8.create_matrix([[1], [1, 2, 3], [1, 2, 3, 4], [1, 2, 3, 4]])

        self.assertTrue(len(r1.matrix.columns), 2)
        self.assertEqual(r1.warnings, [
            'Dropped 1 extra column from dataset.'
            ' Keeping first 2 columns.'
            ' To avoid this behavior, ensure that each row in the dataset has'
            ' the same number of columns.'
        ])

        self.assertTrue(len(r2.matrix.columns), 1)
        self.assertEqual(r2.warnings, [
            'Dropped 3 extra columns from dataset.'
            ' Keeping first 1 column.'
            ' To avoid this behavior, ensure that each row in the dataset has'
            ' the same number of columns.'
        ])

    def test_creating_simple_matrix_with_schema(self):
        rows = [
            ['hi', True],
            ['bye', False],
        ]
        schema = [
            {'name': 'msg', 'role': 'textual'},
            {'name': 'flag', 'role': 'encoded'},
        ]
        report = autom8.create_matrix({'rows': rows, 'schema': schema})

        c1, c2 = report.matrix.columns
        e1 = np.array(['hi', 'bye'], dtype=object)
        e2 = np.array([True, False], dtype=None)

        self.assertTrue(np.array_equal(c1.values, e1))
        self.assertTrue(np.array_equal(c2.values, e2))

        self.assertEqual(c1.name, 'msg')
        self.assertEqual(c2.name, 'flag')

        self.assertEqual(c1.role, 'textual')
        self.assertEqual(c2.role, 'encoded')

        self.assertEqual(c1.is_original, True)
        self.assertEqual(c2.is_original, True)

        self.assertEqual(report.warnings, [])

    def test_creating_simple_matrix_from_list(self):
        report = autom8.create_matrix([
            ['hi', 1, True],
            ['bye', 2, False],
        ])

        c1, c2, c3 = report.matrix.columns
        e1 = np.array(['hi', 'bye'], dtype=object)
        e2 = np.array([1, 2], dtype=None)
        e3 = np.array([True, False], dtype=None)

        self.assertTrue(np.array_equal(c1.values, e1))
        self.assertTrue(np.array_equal(c2.values, e2))
        self.assertTrue(np.array_equal(c3.values, e3))

        self.assertEqual(c1.name, 'Column-1')
        self.assertEqual(c2.name, 'Column-2')
        self.assertEqual(c3.name, 'Column-3')

        self.assertEqual(c1.role, None)
        self.assertEqual(c2.role, None)
        self.assertEqual(c3.role, None)

        self.assertEqual(c1.is_original, True)
        self.assertEqual(c2.is_original, True)
        self.assertEqual(c3.is_original, True)

        self.assertEqual(report.warnings, [])

    def test_len_method(self):
        r1 = autom8.create_matrix([
            ['hi', 1, True],
            ['so', 2, True],
            ['bye', 3, False],
        ])
        r2 = autom8.create_matrix([[1], [2], [3], [4], [5], [6], [7]])
        self.assertEqual(len(r1.matrix), 3)
        self.assertEqual(len(r2.matrix), 7)

    def test_copy_method(self):
        r1 = autom8.create_matrix([
            ['hi', 1.1, True],
            ['so', 2.2, True],
            ['bye', 3.3, False],
        ])
        r2 = autom8.create_matrix([[1.0], [2.0], [3.0], [4.0], [5.0], [6.0]])
        m1, m2 = r1.matrix, r2.matrix
        n1, n2 = m1.copy(), m2.copy()

        self.assertTrue(m1 is not n1)
        self.assertTrue(m2 is not n2)

        self.assertEqual(len(m1.columns), len(n1.columns))
        self.assertEqual(len(m2.columns), len(n2.columns))

        for a, b in zip(m1.columns + m2.columns, n1.columns + n2.columns):
            self.assertTrue(a is not b)
            self.assertTrue(a.values is not b.values)
            self.assertEqual(a.name, b.name)
            self.assertEqual(a.role, b.role)
            self.assertEqual(a.is_original, b.is_original)
            self.assertTrue(np.array_equal(a.values, b.values))

    def test_schema_property(self):
        schema = [
            {'name': 'A', 'role': 'textual'},
            {'name': 'B', 'role': 'encoded'},
            {'name': 'C', 'role': None},
        ]
        report = autom8.create_matrix({'rows': [[1, 2, 3]], 'schema': schema})
        self.assertEqual(report.matrix.schema, schema)

    def test_tolist_method(self):
        r1 = autom8.create_matrix({
            'rows': [['hi', True], ['bye', False]],
            'schema': [
                {'name': 'msg', 'role': 'textual'},
                {'name': 'flag', 'role': 'encoded'},
            ],
        })
        r2 = autom8.create_matrix([[1, 2.0], [3, 4.0], [5, 6.0]])

        self.assertEqual(r1.matrix.tolist(), [
            ['msg', 'flag'],
            ['hi', True],
            ['bye', False],
        ])

        self.assertEqual(r2.matrix.tolist(), [
            ['Column-1', 'Column-2'],
            [1, 2.0],
            [3, 4.0],
            [5, 6.0],
        ])

    def test_to_array_method(self):
        r1 = autom8.create_matrix([[1], [2], [3], [4]])
        r2 = autom8.create_matrix([[1, 2], [3, 4], [5, 6]])
        self.assertTrue(np.array_equal(r1.matrix.to_array(), np.array([1, 2, 3, 4])))
        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*one column'):
            r2.matrix.to_array()

    def test_append_column(self):
        matrix = autom8.create_matrix([[1], [2], [3], [4]]).matrix
        matrix.append_column(np.array([2, 4, 6, 8]), 'foo', 'encoded')
        c1, c2 = matrix.columns
        self.assertEqual(c2.name, 'foo')
        self.assertEqual(c2.role, 'encoded')
        self.assertEqual(c2.is_original, False)
        self.assertTrue(np.array_equal(c2.values, np.array([2, 4, 6, 8])))
        self.assertFalse(np.array_equal(c2.values, np.array([1, 2, 3, 4])))

    def test_drop_columns_by_index(self):
        m1 = autom8.create_matrix([[1, 2, 3], [4, 5, 6], [7, 8, 9]]).matrix
        m2 = autom8.create_matrix([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]).matrix
        m1.drop_columns_by_index([0, 2])
        m2.drop_columns_by_index([1, 2])
        self.assertEqual(len(m1.columns), 1)
        self.assertEqual(len(m2.columns), 2)
        self.assertTrue(np.array_equal(m1.columns[0].values, np.array([2, 5, 8])))
        self.assertEqual(m1.tolist(), [['Column-2'], [2], [5], [8]])
        self.assertEqual(m2.tolist(), [
            ['Column-1', 'Column-4'], [1, 4], [5, 8], [9, 12]
        ])

    def test_select_rows(self):
        mat = autom8.create_matrix([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]).matrix
        m1 = mat.select_rows([0, 2, 4])
        m2 = mat.select_rows([1, 3])
        head = ['Column-1', 'Column-2']
        self.assertEqual(m1.tolist(), [head, [1, 2], [5, 6], [9, 10]])
        self.assertEqual(m2.tolist(), [head, [3, 4], [7, 8]])

    def test_exclude_rows(self):
        mat = autom8.create_matrix([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10]]).matrix
        m1 = mat.exclude_rows([0, 2, 4])
        m2 = mat.exclude_rows([1, 3])
        head = ['Column-1', 'Column-2']
        self.assertEqual(m1.tolist(), [head, [3, 4], [7, 8]])
        self.assertEqual(m2.tolist(), [head, [1, 2], [5, 6], [9, 10]])

    def test_select_columns(self):
        mat = autom8.create_matrix([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]).matrix
        m1 = mat.select_columns([0, 2, 3])
        m2 = mat.select_columns([1])
        self.assertEqual(m1.tolist()[1:], [[1, 3, 4], [5, 7, 8], [9, 11, 12]])
        self.assertEqual(m2.tolist()[1:], [[2], [6], [10]])

    def test_exclude_columns(self):
        mat = autom8.create_matrix([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]).matrix
        m1 = mat.exclude_columns([0, 2, 3])
        m2 = mat.exclude_columns([1])
        self.assertEqual(m1.tolist()[1:], [[2], [6], [10]])
        self.assertEqual(m2.tolist()[1:], [[1, 3, 4], [5, 7, 8], [9, 11, 12]])

    def test_column_indices_where(self):
        report = autom8.create_matrix([[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]])
        pred = lambda x: x.name == 'Column-2' or x.name == 'Column-4'
        indices = report.matrix.column_indices_where(pred)
        self.assertEqual(indices, [1, 3])


class TestColumn(unittest.TestCase):
    def test_len_method(self):
        report = autom8.create_matrix([[1, 2], [3, 4], [5, 6], [7, 8]])
        c1, c2 = report.matrix.columns
        self.assertEqual(len(c1), 4)
        self.assertEqual(len(c2), 4)

    def test_column_dtype_property(self):
        report = autom8.create_matrix([
            ['hi', 10, 1.1, True, None],
            ['so', 20, 2.2, True, None],
            ['bye', 30, 3.3, False, None],
        ])
        c1, c2, c3, c4, c5 = report.matrix.columns
        self.assertEqual(c1.dtype, np.dtype('O'))
        self.assertEqual(c2.dtype, np.dtype('int64'))
        self.assertEqual(c3.dtype, np.dtype('float64'))
        self.assertEqual(c4.dtype, np.dtype('bool'))
        self.assertEqual(c5.dtype, np.dtype('O'))

    def test_properties_of_valid_roles(self):
        report = autom8.create_matrix([
            [1, 2, 3, 4, 'a'],
            [2, 3, 4, 5, 'b'],
            [3, 4, 5, 6, 'c'],
        ])
        c1, c2, c3, c4, c5 = report.matrix.columns
        c1.role = None
        c2.role = 'categorical'
        c3.role = 'encoded'
        c4.role = 'numerical'
        c5.role = 'textual'

        self.assertFalse(c1.is_numerical)
        self.assertFalse(c2.is_numerical)
        self.assertFalse(c3.is_numerical)
        self.assertTrue(c4.is_numerical)
        self.assertFalse(c5.is_numerical)

        self.assertIsNone(c1.role)
        self.assertEqual(c2.role, 'categorical')
        self.assertEqual(c3.role, 'encoded')
        self.assertEqual(c4.role, 'numerical')
        self.assertEqual(c5.role, 'textual')

    def test_setting_an_invalid_role(self):
        report = autom8.create_matrix([[1], [2], [3]])
        col = report.matrix.columns[0]
        with self.assertRaisesRegex(autom8.AutoM8Exception, 'Expected.*role in'):
            col.role = 'foo'


if __name__ == '__main__':
    unittest.main()
