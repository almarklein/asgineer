import random

import asgineer.utils

from common import make_server, get_backend

from pytest import raises, skip


compressable_data = b"x" * 1000
uncompressable_data = bytes([int(random.uniform(0, 255)) for i in range(1000)])

# def test_normalize_response()  -> tested as part of test_app


def test_make_asset_handler_fails():

    if get_backend() != "mock":
        skip("Can only test this with mock server")

    with raises(TypeError):
        asgineer.utils.make_asset_handler("not a dict")
    with raises(ValueError):
        asgineer.utils.make_asset_handler({"notstrorbytes": 4})


def test_make_asset_handler():

    if get_backend() != "mock":
        skip("Can only test this with mock server")

    # Make a server
    assets = {
        "foo.html": "bla",
        "foo.bmp": compressable_data,
        "foo.png": uncompressable_data,
    }
    assets.update({"b.xx": b"x", "t.xx": "x", "h.xx": "<html>x</html>"})
    assets.update({"big.html": "x" * 10000, "bightml": "<html>" + "x" * 100000})
    handler = asgineer.utils.make_asset_handler(assets)
    server = make_server(asgineer.to_asgi(handler))

    # Do some wrong requestrs
    r0a = server.get("foo")
    r0b = server.put("foo.html")

    assert r0a.status == 404
    assert r0b.status == 405

    # Do simple requests and check validity
    r1a = server.get("foo.html")
    r1b = server.request("head", "foo.html")
    r2a = server.get("foo.bmp")
    r2b = server.get("foo.png")

    assert r1a.status == 200 and r1b.status == 200
    assert len(r1a.body) == 3
    assert len(r1b.body) == 0  # HEAD's have no body

    for r in (r1a, r1b):
        assert r.headers["content-type"] == "text/html"
        assert int(r.headers["content-length"]) == 3

    assert r2a.status == 200 and r2b.status == 200
    assert r2b.headers["content-type"] == "image/png"
    assert len(r2a.body) == 1000 and len(r2b.body) == 1000

    assert server.get("h.xx").headers["content-type"] == "text/html"
    assert server.get("t.xx").headers["content-type"] == "text/plain"
    assert server.get("b.xx").headers["content-type"] == "application/octet-stream"

    assert r1a.headers["etag"]
    assert "max-age=0" in [x.strip() for x in r1a.headers["cache-control"].split(",")]
    assert r2a.headers["etag"]
    assert r2b.headers["etag"]
    assert r2a.headers["etag"] != r2b.headers["etag"]

    assert r1a.headers.get("content-encoding", "identity") == "identity"
    assert r2a.headers.get("content-encoding", "identity") == "identity"
    assert r2b.headers.get("content-encoding", "identity") == "identity"

    # Now do request with gzip on
    r3 = server.get("foo.html", headers={"accept-encoding": "gzip"})
    r4a = server.get("foo.bmp", headers={"accept-encoding": "gzip"})
    r4b = server.get("foo.png", headers={"accept-encoding": "gzip"})

    assert r3.status == 200 and r4a.status == 200 and r4b.status == 200
    assert len(r3.body) == 3 and len(r4a.body) < 50 and len(r4b.body) == 1000

    assert r3.headers.get("content-encoding", "identity") == "identity"  # small
    assert r4a.headers.get("content-encoding", "identity") == "gzip"  # big enough
    assert r4b.headers.get("content-encoding", "identity") == "identity"  # entropy

    # Now do a request with etag
    r5 = server.get(
        "foo.html",
        headers={"accept-encoding": "gzip", "if-none-match": r1a.headers["etag"]},
    )
    r6 = server.get(
        "foo.png",
        headers={"accept-encoding": "gzip", "if-none-match": r2b.headers["etag"]},
    )

    assert r5.status == 304 and r6.status == 304
    assert len(r5.body) == 0 and len(r6.body) == 0

    assert r5.headers.get("content-encoding", "identity") == "identity"
    assert r6.headers.get("content-encoding", "identity") == "identity"

    # Dito, but with wrong etag
    r7 = server.get(
        "foo.html",
        headers={"accept-encoding": "gzip", "if-none-match": r2b.headers["etag"]},
    )
    r8 = server.get(
        "foo.png", headers={"accept-encoding": "gzip", "if-none-match": "xxxx"}
    )

    assert r7.status == 200 and r8.status == 200
    assert len(r7.body) == 3 and len(r8.body) == 1000

    # Big html files will be zipped, but must retain content type
    for fname in ("big.html", "bightml"):
        r = server.get(fname)
        assert r.status == 200
        assert r.headers.get("content-encoding", "identity") == "identity"
        assert r.headers["content-type"] == "text/html"
        plainbody = r.body

        r = server.get(fname, headers={"accept-encoding": "gzip"})
        assert r.status == 200
        assert r.headers.get("content-encoding", "identity") == "gzip"
        assert r.headers["content-type"] == "text/html"
        assert len(r.body) < len(plainbody)


def test_make_asset_handler_max_age():
    if get_backend() != "mock":
        skip("Can only test this with mock server")

    # Make a server
    assets = {
        "foo.html": "bla",
        "foo.bmp": compressable_data,
        "foo.png": uncompressable_data,
    }
    handler = asgineer.utils.make_asset_handler(assets, max_age=9999)
    server = make_server(asgineer.to_asgi(handler))

    # Do simple requests and check validity
    r1 = server.get("foo.html")
    assert r1.status == 200

    assert r1.headers["etag"]
    assert "max-age=9999" in [x.strip() for x in r1.headers["cache-control"].split(",")]


if __name__ == "__main__":
    test_make_asset_handler_fails()
    test_make_asset_handler()
    test_make_asset_handler_max_age()
