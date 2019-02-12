"""
Simple Asgish hanler to show information about the incoming request.
"""

import asgish


@asgish.to_asgi
async def main(request):

    lines = [
        "<!DOCTYPE html><html><meta><meta charset='UTF-8'></meta><body>",
        f"<h2>request.method</h2>{request.method}",
        f"<h2>request.url</h2>{request.url}",
        f"<h2>request.path</h2>{request.path}",
        f"<h2>request.querydict</h2>{request.querydict}",
        f"<h2>request.headers</h2>",
        "<br>".join(f"{key}: {val!r}" for key, val in request.headers.items()),
        "<br>",
        "</body></html>",
    ]
    return "<br>".join(lines)


if __name__ == "__main__":
    asgish.run(main, "uvicorn", "localhost:8080")
