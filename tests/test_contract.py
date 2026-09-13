"""Contract with the frontend (chapter 11): the ui test catalog is the golden and validates."""

import json
from pathlib import Path

import pytest

from manager.models import Catalog

from .conftest import EXPECTED

UI_FIXTURE = (
    Path(__file__).parents[2] / "hubandcircles-ui" / "src" / "test" / "fixtures" / "catalog.json"
)

pytestmark = pytest.mark.skipif(not UI_FIXTURE.is_file(), reason="ui repo not checked out beside")


def test_ui_fixture_validates_and_equals_golden():
    ui = json.loads(UI_FIXTURE.read_text(encoding="utf-8"))
    Catalog.model_validate(ui)
    golden = json.loads((EXPECTED / "catalog.json").read_text(encoding="utf-8"))
    del ui["generated_at"], golden["generated_at"]
    assert ui == golden
