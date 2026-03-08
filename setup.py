import sys
from pathlib import Path
from setuptools import setup, find_packages


min_version = (3, 10)
if sys.version_info < min_version:
    raise RuntimeError(
        f"Python version is {sys.version_info}. Requires 3.10 or greater."
    )


def read(fname):
    with open(Path(__file__).parent / fname) as f:
        return f.read()


setup(
    name="web-monitoring-pdf-diff",
    version="0.1.0",
    description="Tools for diffing PDF documents, producing output compatible "
                "with web-monitoring-diff.",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="Internet Archive",
    url="https://github.com/internetarchive/web-monitoring-pdf-diff",
    python_requires=">={}".format(".".join(str(n) for n in min_version)),
    packages=find_packages(exclude=["tests"]),
    license="AGPL-3.0-only",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    install_requires=[
        "PyMuPDF",
        "Pillow",
    ],
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
        ],
    },
)
