import asgish


def test_namespace():
    assert asgish.__version__

    ns = set(name for name in dir(asgish) if not name.startswith("_"))

    assert ns == {
        "BaseRequest",
        "BaseRequest",
        "HttpRequest",
        "WebsocketRequest",
        "to_asgi",
        "run",
    }
    assert ns == set(asgish.__all__)


if __name__ == "__main__":
    test_namespace()
