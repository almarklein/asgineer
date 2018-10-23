"""
invoke tasks
"""

import os
import sys
import shutil

from invoke import task

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(THIS_DIR, "docs")
DOC_BUILD_DIR = os.path.join(THIS_DIR, "docs", "_build")


@task
def clean(ctx):
    """ clean files from testing/building/etc
    """
    for dname in [
        ".cache",
        ".hypothesis",
        ".pytest_cache",
        "build",
        "dist",
        "htmlcov",
        "asgish.egg-info",
        "asgish/__pycache__",
        "tests/__pycache__",
        "docs/_build",
    ]:
        dirname = os.path.join(THIS_DIR, dname)
        if os.path.isdir(dirname):
            print("removing", dname)
            shutil.rmtree(dirname)

    for fname in [".coverage"]:
        filename = os.path.join(THIS_DIR, fname)
        if os.path.isfile(filename):
            print("removing", fname)
            os.remove(filename)


@task
def tests(ctx, server="mock"):
    """ run unit tests
    """
    import pytest  # noqa

    test_path = "tests"
    os.environ["ASGI_SERVER"] = server
    res = pytest.main(
        ["-v", "--cov=asgish", "--cov-report=term", "--cov-report=html", test_path]
    )
    sys.exit(res)


@task(
    help=dict(
        clean="clear the doc output; start fresh",
        build="build html docs",
        show="show the docs in the browser.",
    )
)
def docs(ctx, clean=False, build=False, show=False, **kwargs):
    """ make API documentation
    """
    # Prepare

    if not (clean or build or show):
        sys.exit('Task "docs" must be called with --clean, --build or --show')

    if clean:
        sphinx_clean(DOC_BUILD_DIR)

    if build:
        sphinx_build(DOC_DIR, DOC_BUILD_DIR)

    if show:
        sphinx_show(os.path.join(DOC_BUILD_DIR, "html"))


def sphinx_clean(build_dir):
    if os.path.isdir(build_dir):
        shutil.rmtree(build_dir)
    os.mkdir(build_dir)
    os.mkdir(os.path.join(build_dir, "html"))
    print("Cleared build directory.")


def sphinx_build(src_dir, build_dir):
    import sphinx

    cmd = [
        "-b",
        "html",
        "-d",
        os.path.join(build_dir, "doctrees"),
        src_dir,  # Source
        os.path.join(build_dir, "html"),  # Dest
    ]

    if sphinx.version_info > (1, 7):
        import sphinx.cmd.build

        ret = sphinx.cmd.build.build_main(cmd)
    else:
        ret = sphinx.build_main(["sphinx-build"] + cmd)
    if ret != 0:
        raise RuntimeError("Sphinx error: %s" % ret)
    print("Build finished. The HTML pages are in %s/html." % build_dir)


def sphinx_show(html_dir):
    index_html = os.path.join(html_dir, "index.html")
    if not os.path.isfile(index_html):
        sys.exit("Cannot show pages, build the html first.")
    import webbrowser

    webbrowser.open_new_tab(index_html)
