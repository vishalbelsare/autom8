import io
import json
import pickle
import pprint
from datetime import date
from string import Template
from zipfile import ZipFile

import category_encoders
import numpy
import pandas
import sklearn
import scipy

try:
    import lightgbm
except ImportError:
    lightgbm = None

try:
    import xgboost
except ImportError:
    xgboost = None

from .matrix import create_matrix, drop_empty_rows, Matrix


def create_package(package_name, pipeline, dataset, test_indices, receiver=None):
    if not isinstance(dataset, Matrix):
        dataset = drop_empty_rows(dataset)

    matrix = create_matrix(dataset, receiver=receiver)
    target_column = matrix.column_names.index(pipeline.predicts_column)
    matrix.drop_columns_by_index(target_column)
    sample_input = matrix.select_rows(test_indices[:2]).tolist()

    args = _template_args(package_name, pipeline, sample_input)
    result = io.BytesIO()
    templates = {
        'Dockerfile': dockerfile,
        'LICENSE': license,
        'Makefile': makefile,
        'README.md': readme,
        'requirements.txt': requirements,
        'service.py': service,
        'tests.py': tests,
    }
    with ZipFile(result, 'w') as out:
        out.writestr(f'{package_name}/pipeline.pickle', pickle.dumps(pipeline))
        for file_name, template in templates.items():
            contents = Template(template).substitute(args).strip() + '\n'
            out.writestr(f'{package_name}/{file_name}', contents.encode('utf-8'))
    return result.getvalue()


def _template_args(package_name, pipeline, sample_input):
    est = pipeline.estimator
    extra_packages = []

    if lightgbm is not None:
        if isinstance(est, (lightgbm.LGBMRegressor, lightgbm.LGBMClassifier)):
            extra_packages.append(f'lightgbm=={lightgbm.__version__}')

    if xgboost is not None:
        if isinstance(est, (xgboost.XGBRegressor, xgboost.XGBClassifier)):
            extra_packages.append(f'xgboost=={xgboost.__version__}')

    sample_input = [pipeline.input_columns] + sample_input
    sample_result = pipeline.run(sample_input)
    sample_output = {
        'columnName': f'Predicted {pipeline.predicts_column}',
        'predictions': sample_result.predictions,
        'probabilities': sample_result.probabilities,
    }

    return {
        # Use github for now, until autom8 is published to PyPI.
        'AUTOM8_PACKAGE': 'git+git://github.com/jvs/autom8.git@380b6f610432d3d805e43d4bf504e5275a0bcc42#egg=autom8',
        'ESTIMATOR_CLASS': type(pipeline.estimator).__name__,
        'EXTRA_PACKAGES': '\n'.join(extra_packages),
        'IMAGE_NAME': package_name,
        'PACKAGE_NAME': package_name,
        'PACKAGE_NAME_REPR': repr(package_name),
        'PREDICTED_COLUMN': pipeline.predicts_column,
        'PREDICTED_COLUMN_REPR': repr(f'Predicted {pipeline.predicts_column}'),
        'README_INPUT_COLUMNS': '\n'.join(f'  -  {c}'
            for c in pipeline.input_columns),
        'README_INPUT_EXAMPLE': json
            .dumps({'rows': sample_input}, sort_keys=True, indent=2)
            .replace("'", '\'\"\'\"\'').replace('\n', '\n        '),
        'README_OUTPUT_EXAMPLE': json
            .dumps(sample_output, sort_keys=True, indent=2)
            .replace('\n', '\n    '),
        'TEST_INPUT': pformat(sample_input),
        'TEST_OUTPUT_PREDICTIONS': pformat(sample_result.predictions),
    }


def pformat(obj):
    return pprint.pformat(obj, indent=2).replace('\n', '\n  ')


dockerfile = '''
FROM python:3.6.4

WORKDIR /deploy
COPY requirements.txt /deploy
RUN pip3 install --no-cache-dir --disable-pip-version-check -r requirements.txt

COPY service.py /deploy
COPY pipeline.pickle /deploy

CMD ["gunicorn", "service:app", "--workers=1", "--bind", "0.0.0.0:80"]
'''


license = '''
MIT License

Copyright (c) 2018 jvs

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''


makefile = '''
.PHONY: image container stop

clean:
    rm -rf __pycache__/*.pyc

image:
    docker build -t $IMAGE_NAME .

container: image
    docker run \\
        --name $IMAGE_NAME \\
        --rm \\
        -p 0.0.0.0:5118:80 \\
        $IMAGE_NAME

stop:
    docker stop $IMAGE_NAME

test: clean virtualenv
    .virtualenv/bin/pytest -s -v -W "ignore::PendingDeprecationWarning" tests.py

virtualenv: .virtualenv/bin/activate

.virtualenv/bin/activate: requirements.txt
    test -d .virtualenv || virtualenv .virtualenv
    .virtualenv/bin/pip install -U -r requirements.txt
    .virtualenv/bin/pip install -U pytest
    touch .virtualenv/bin/activate
'''.replace('    ', '\t')


readme = '''
# $PACKAGE_NAME

This project provides a web service for predicting `$PREDICTED_COLUMN`.


## Summary

- Estimator: $ESTIMATOR_CLASS
- Predicts: $PREDICTED_COLUMN
- Inputs:
$README_INPUT_COLUMNS


## Requirements

- make
- docker
- virtualenv


## Quick Start

Run the command `make container` to start the web service.

To get predictions, send a POST request to `/predict`:

    curl --header "Content-Type: application/json" \\
        --data '$README_INPUT_EXAMPLE' \\
        http://localhost:5118/predict

This will return:

    $README_OUTPUT_EXAMPLE


## Commands

- `make container`
  - Runs the web service in a docker container.
  - Maps local port 5118 to the container's port 80.
- `make stop`
  - Stops the container.
- `make image`
  - Builds the docker image.
- `make test`
  - Runs the test script in a virtual environment.
'''


requirements = f'''
$AUTOM8_PACKAGE
category-encoders=={category_encoders.__version__}
flask==1.0.2
gunicorn==19.8.1
numpy=={numpy.__version__}
pandas=={pandas.__version__}
scikit-learn=={sklearn.__version__}
scipy=={scipy.__version__}
$EXTRA_PACKAGES
'''


# TODO: Include an autom8 receiver when calling pipeline.run.
service = '''
import pickle
import flask

app = flask.Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

with open('pipeline.pickle', 'rb') as f:
    pipeline = pickle.load(f)


@app.route('/', methods=['GET'])
def health_check():
    return $PACKAGE_NAME_REPR


@app.route('/describe', methods=['GET'])
def describe():
    return flask.jsonify({
        'inputColumns': pipeline.input_columns,
        'predictsColumn': pipeline.predicts_column,
        'predictsClasses': pipeline.predicts_classes.tolist(),
        'estimatorClass': type(pipeline.estimator).__name__,
        'estimator': repr(pipeline.estimator),
    })


@app.route('/predict', methods=['POST'])
def predict():
    try:
        result = pipeline.run(flask.request.json['rows'])
        return flask.jsonify({
            'columnName': f'Predicted {pipeline.predicts_column}',
            'predictions': result.predictions,
            'probabilities': result.probabilities,
        })
    except Exception:
        app.logger.exception('Failed to make predictions')
        raise
'''


tests = '''
import pickle
import service


SAMPLE_INPUT = $TEST_INPUT

SAMPLE_PREDICTIONS = $TEST_OUTPUT_PREDICTIONS


def test_pipeline_run_method():
    with open('pipeline.pickle', 'rb') as f:
        pipeline = pickle.load(f)
    result = pipeline.run(SAMPLE_INPUT)
    assert result.predictions == SAMPLE_PREDICTIONS


def test_index():
    client = service.app.test_client()
    response = client.get('/')
    assert response.data.decode('utf-8') == $PACKAGE_NAME_REPR


def test_predict():
    client = service.app.test_client()
    response = client.post('/predict', json={'rows': SAMPLE_INPUT})
    doc = response.get_json()
    assert doc['columnName'] == PREDICTED_COLUMN_REPR
    assert doc['predictions'] == SAMPLE_PREDICTIONS
'''
