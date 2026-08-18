import sys


def test_python_311_is_used() -> None:
    assert sys.version_info[:2] == (3, 11)
