import copy
from pathlib import Path

import pytest

from yassa.app import execute, prepare
from yassa.records import canonical, parse_json

REPOSITORY = Path(__file__).resolve().parents[1]


@pytest.fixture
def study_data():
    data = parse_json((REPOSITORY / "studies/fixture-study.json").read_bytes())
    data["conditions"][0]["source_path"] = str(REPOSITORY / "studies/fixture-supplied.json")
    return data


@pytest.fixture
def write_study(tmp_path, study_data):
    def write(data=None):
        path = tmp_path / "request.json"
        path.write_bytes(canonical(data if data is not None else study_data))
        return path

    return write


@pytest.fixture(scope="session")
def completed_run(tmp_path_factory):
    directory = tmp_path_factory.mktemp("complete-path")
    request = copy.deepcopy(parse_json((REPOSITORY / "studies/fixture-study.json").read_bytes()))
    request["conditions"][0]["source_path"] = str(REPOSITORY / "studies/fixture-supplied.json")
    study_path = directory / "request.json"
    study_path.write_bytes(canonical(request))
    root = prepare(study_path, directory / "run")
    execute(root)
    return root
