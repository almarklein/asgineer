"""
Test some meta stuff.
"""

import os
import asgineer


def test_namespace():
    assert asgineer.__version__

    ns = set(name for name in dir(asgineer) if not name.startswith("_"))

    ns.discard("testutils")  # may or may not be imported

    assert ns == {
        "BaseRequest",
        "HttpRequest",
        "RequestSet",
        "WebsocketRequest",
        "DisconnectedError",
        "to_asgi",
        "run",
        "utils",
        "sleep",
    }
    assert ns == set(asgineer.__all__)


def test_newlines():
    # Let's be a bit pedantic about sanitizing whitespace :)

    for root, dirs, files in os.walk(os.path.dirname(os.path.abspath(__file__))):
        for fname in files:
            if fname.endswith((".py", ".md", ".rst", ".yml")):
                with open(os.path.join(root, fname), "rb") as f:
                    text = f.read().decode()
                    assert "\r" not in text, f"{fname} has CR!"
                    assert "\t" not in text, f"{fname} has tabs!"


if __name__ == "__main__":
    test_namespace()
    test_newlines()
