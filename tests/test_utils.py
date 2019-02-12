import asgish.utils

from common import make_server, get_backend

from pytest import raises, skip


# def test_normalize_response()  -> tested as part of test_app


def test_make_asset_handler():

    if get_backend() != "mock":
        skip("Can only test this with mock server")

    with raises(TypeError):
        asgish.utils.make_asset_handler("not a dict")
    with raises(ValueError):
        asgish.utils.make_asset_handler({"notstrorbytes": 4})

    # Make a server
    assets = {"foo.html": "bla", "foo.png": b"x" * 10000}
    assets.update({"b.xx": b"x", "t.xx": "x", "h.xx": "<html>x</html>"})
    handler = asgish.utils.make_asset_handler(assets)
    server = make_server(asgish.to_asgi(handler))

    # Do simple requests and check validity
    r0 = server.get("foo")
    r1 = server.get("foo.html")
    r2 = server.get("foo.png")

    assert r0.status == 404
    assert r1.status == 200 and r2.status == 200
    assert len(r1.body) == 3 and len(r2.body) == 10000

    assert r1.headers["content-type"] == "text/html"
    assert r2.headers["content-type"] == "image/png"

    assert server.get("h.xx").headers["content-type"] == "text/html"
    assert server.get("t.xx").headers["content-type"] == "text/plain"
    assert server.get("b.xx").headers["content-type"] == "application/octet-stream"

    assert r1.headers["etag"]
    assert r2.headers["etag"]
    assert r1.headers["etag"] != r2.headers["etag"]

    assert r1.headers.get("content-encoding", "identity") == "identity"
    assert r2.headers.get("content-encoding", "identity") == "identity"

    # Now do request with gzip on
    r3 = server.get("foo.html", headers={"accept-encoding": "gzip"})
    r4 = server.get("foo.png", headers={"accept-encoding": "gzip"})

    assert r3.status == 200 and r4.status == 200
    assert len(r3.body) == 3 and len(r4.body) < 100

    assert r3.headers.get("content-encoding", "identity") == "identity"  # small
    assert r4.headers.get("content-encoding", "identity") == "gzip"  # big enough

    # Now do a request with etag
    r5 = server.get(
        "foo.html",
        headers={"accept-encoding": "gzip", "if-none-match": r1.headers["etag"]},
    )
    r6 = server.get(
        "foo.png",
        headers={"accept-encoding": "gzip", "if-none-match": r2.headers["etag"]},
    )

    assert r5.status == 304 and r6.status == 304
    assert len(r5.body) == 0 and len(r6.body) == 0

    assert r5.headers.get("content-encoding", "identity") == "identity"
    assert r6.headers.get("content-encoding", "identity") == "identity"

    # Dito, but with wrong etag
    r7 = server.get(
        "foo.html",
        headers={"accept-encoding": "gzip", "if-none-match": r2.headers["etag"]},
    )
    r8 = server.get(
        "foo.png", headers={"accept-encoding": "gzip", "if-none-match": "xxxx"}
    )

    assert r7.status == 200 and r8.status == 200
    assert len(r1.body) == 3 and len(r2.body) == 10000


if __name__ == "__main__":
    test_make_asset_handler()
