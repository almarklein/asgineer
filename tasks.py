""" Invoke tasks for imageio-ffmpeg
"""

import os
import sys
import shutil
import importlib
import subprocess

from invoke import task

# ---------- Per project config ----------

NAME = "asgineer"
LIBNAME = NAME.replace("-", "_")
PY_PATHS = [
    LIBNAME,
    "examples",
    "tests",
    "tasks.py",
    "setup.py",
]

# ----------------------------------------

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if not os.path.isdir(os.path.join(ROOT_DIR, LIBNAME)):
    sys.exit("package NAME seems to be incorrect.")


@task
def tests(ctx, server="mock", cover=False):
    """Perform unit tests. Use --cover to open a webbrowser to show coverage."""
    import pytest  # noqa

    test_path = "tests"
    os.environ["ASGI_SERVER"] = server
    res = pytest.main(
        ["-v", "--cov=asgineer", "--cov-report=term", "--cov-report=html", test_path]
    )
    if res:
        sys.exit(res)
    if cover:
        import webbrowser

        webbrowser.open(os.path.join(ROOT_DIR, "htmlcov", "index.html"))


@task
def lint(ctx):
    """Validate the code style (e.g. undefined names)"""
    try:
        importlib.import_module("flake8")
    except ImportError:
        sys.exit("You need to ``pip install flake8`` to lint")

    # We use flake8 with minimal settings
    # http://pep8.readthedocs.io/en/latest/intro.html#error-codes
    cmd = [sys.executable, "-m", "flake8"] + PY_PATHS + ["--select=F,E11"]
    ret_code = subprocess.call(cmd, cwd=ROOT_DIR)
    if ret_code == 0:
        print("No style errors found")
    else:
        sys.exit(ret_code)


@task
def checkformat(ctx):
    """Check whether the code adheres to the style rules. Use autoformat to fix."""
    black_wrapper(False)


@task
def autoformat(ctx):
    """Automatically format the code (using black)."""
    black_wrapper(True)


def black_wrapper(writeback):
    """Helper function to invoke black programatically."""

    check = [] if writeback else ["--check"]
    exclude = "|".join(["cangivefilenameshere"])
    sys.argv[1:] = check + ["--exclude", exclude, ROOT_DIR]

    import black

    black.main()


@task
def clean(ctx):
    """Clean the repo of temp files etc."""
    for root, dirs, files in os.walk(ROOT_DIR):
        for dname in dirs:
            if dname in (
                "__pycache__",
                ".cache",
                "htmlcov",
                ".hypothesis",
                ".pytest_cache",
                "dist",
                "build",
                "_build",
                ".mypy_cache",
                LIBNAME + ".egg-info",
            ):
                shutil.rmtree(os.path.join(root, dname))
                print("Removing", dname)
        for fname in files:
            if fname.endswith((".pyc", ".pyo")) or fname in (".coverage"):
                os.remove(os.path.join(root, fname))
                print("Removing", fname)


DOC_DIR = os.path.join(ROOT_DIR, "docs")
DOC_BUILD_DIR = os.path.join(ROOT_DIR, "docs", "_build")


@task(
    help=dict(
        clean="clear the doc output; start fresh",
        build="build html docs",
        show="show the docs in the browser.",
    )
)
def docs(ctx, clean=False, build=False, show=False, **kwargs):
    """make API documentation"""
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
