import pytest

from netbench.logging_setup import setup_logging


def test_invalid_level_raises() -> None:
    with pytest.raises(ValueError, match="NOT_A_LEVEL"):
        setup_logging("not_a_level")


def test_lowercase_level_is_accepted() -> None:
    setup_logging("debug")
