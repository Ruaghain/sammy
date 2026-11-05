import pytest

from drivers.sammy import SammyDriver


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "built_examples(*rows): the Scenario Outline Examples rows built so far, "
        "each a dict of column values; every other row of that outline is deselected",
    )


def pytest_collection_modifyitems(config, items):
    # Examples rows are built one at a time, like scenarios. @scenario binds a
    # whole outline, so rows not yet built are deselected here, just as
    # unbound scenarios are ignored.
    selected, deselected = [], []
    for item in items:
        marker = item.get_closest_marker("built_examples")
        callspec = getattr(item, "callspec", None)
        row = callspec.params.get("_pytest_bdd_example") if callspec else None
        if marker and row is not None and row not in marker.args:
            deselected.append(item)
        else:
            selected.append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected


@pytest.fixture
def sammy(tmp_path) -> SammyDriver:
    return SammyDriver(tmp_path)
