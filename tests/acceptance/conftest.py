import pytest

from drivers.sammy import SammyDriver


@pytest.fixture
def sammy() -> SammyDriver:
    return SammyDriver()
