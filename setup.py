"""
asgineer setup script.
"""

import os

try:
    import setuptools

    assert setuptools  # fool pyflakes by "using" setuptools
except ImportError:
    pass  # setuptools allows for "develop", but it's not essential

from distutils.core import setup


## Function we need


def get_version_and_doc(filename):
    NS = dict(__version__="", __doc__="")
    docStatus = 0  # Not started, in progress, done
    for line in open(filename, "rb").read().decode().splitlines():
        if line.startswith("__version__"):
            exec(line.strip(), NS, NS)
        elif line.startswith('"""'):
            if docStatus == 0:
                docStatus = 1
                line = line.lstrip('"')
            elif docStatus == 1:
                docStatus = 2
        if docStatus == 1:
            NS["__doc__"] += line.rstrip() + "\n"
    if not NS["__version__"]:
        raise RuntimeError("Could not find __version__")
    return NS["__version__"], NS["__doc__"]


## Collect info for setup()

THIS_DIR = os.path.dirname(__file__)

# Define name and description
name = "asgineer"
description = "A really thin ASGI web framework"

# Get version and docstring (i.e. long description)
version, doc = get_version_and_doc(os.path.join(THIS_DIR, "asgineer", "__init__.py"))


## Setup

setup(
    name=name,
    version=version,
    author="Almar Klein",
    author_email="almar.klein@gmail.com",
    license="(new) BSD",
    url="https://github.com/almarklein/asgineer",
    download_url="https://pypi.org/project/asgineer/",
    keywords="ASGI web framework",
    description=description,
    long_description=doc,
    platforms="any",
    provides=[name],
    python_requires=">=3.6",
    install_requires=[],
    packages=["asgineer"],
    # entry_points={'console_scripts': ['asgi = asgi:cli'], },
    zip_safe=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: BSD License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
)
