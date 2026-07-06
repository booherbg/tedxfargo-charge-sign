from pathlib import Path

import pytest

ASSETS = Path(__file__).parent / "assets"


@pytest.fixture
def bungee() -> str:
    return str(ASSETS / "fonts" / "Bungee-Regular.ttf")


@pytest.fixture
def pacifico() -> str:
    return str(ASSETS / "fonts" / "Pacifico-Regular.ttf")
