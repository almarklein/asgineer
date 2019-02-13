"""
Test some specifics of the run function.
"""

import asgineer
import pytest


async def handler(request):
    return "ok"


def test_run():

    with pytest.raises(ValueError) as err:
        asgineer.run("foo", "nonexistingserver")
    assert "full path" in str(err).lower()

    with pytest.raises(ValueError) as err:
        asgineer.run("foo:bar", "nonexistingserver")
    assert "invalid server" in str(err).lower()

    with pytest.raises(ValueError) as err:
        asgineer.run(handler, "nonexistingserver")
    assert "invalid server" in str(err).lower()


if __name__ == "__main__":
    test_run()
