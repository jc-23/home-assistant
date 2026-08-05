import re
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIRECTORY = Path(__file__).resolve().parent / "fixtures"


class BlueprintLoader(yaml.SafeLoader):
    pass


BlueprintLoader.add_constructor(
    "!input", lambda loader, node: loader.construct_scalar(node)
)


def load_blueprint(path):
    with path.open(encoding="utf-8") as blueprint_file:
        return yaml.load(blueprint_file, Loader=BlueprintLoader)


def load_fixture(name):
    with (FIXTURES_DIRECTORY / name).open(encoding="utf-8") as fixture_file:
        return yaml.safe_load(fixture_file)


def _as_timestamp(value):
    if isinstance(value, (int, float)):
        return value
    return datetime.fromisoformat(value).timestamp()


def _timestamp_custom(value, date_format, local=False):
    timezone = ZoneInfo("Europe/Berlin") if local else ZoneInfo("UTC")
    return datetime.fromtimestamp(value, timezone).strftime(date_format)


def template_environment():
    environment = Environment()
    environment.filters["as_timestamp"] = _as_timestamp
    environment.filters["timestamp_custom"] = _timestamp_custom
    environment.filters["regex_replace"] = re.sub
    environment.tests["search"] = (
        lambda value, pattern: re.search(pattern, value) is not None
    )
    return environment


def state(attributes):
    return SimpleNamespace(attributes=attributes)


def state_trigger(trigger_id, current=None, previous=None):
    return SimpleNamespace(
        id=trigger_id,
        to_state=None if current is None else state(current),
        from_state=None if previous is None else state(previous),
    )


def event_trigger(trigger_id, current=None, previous=None):
    return SimpleNamespace(
        id=trigger_id,
        event=SimpleNamespace(
            data=SimpleNamespace(
                new_state=None if current is None else state(current),
                old_state=None if previous is None else state(previous),
            )
        ),
    )
