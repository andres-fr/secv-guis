# -*- coding:utf-8 -*-


"""
Deploy script for the package. It has to be in the repository root directory.
Make sure that the config entries are correct!
"""


import setuptools


# See https://stackoverflow.com/a/33685899/4511978
REQUIREMENTS = [
    "flake8",
    "coverage",
    "snakeviz",
    # "memory_profiler",
    "sphinx",
    "sphinx_rtd_theme",
    "bump2version",
    "setuptools",
    "wheel",
    "twine",
    # "mypy",
    #
    "ExifRead",
    "randomcolor",
    "numpy",
    "scikit-image",
    "PySide2"]


def setup():
    """
    The proper setup function, adapted from the tutorial in
    https://packaging.python.org/tutorials/packaging-projects/
    """
    with open("README.md", "r") as f:
        long_description = f.read()
    #
    setuptools.setup(
        name="secv_guis",
        # the version is automatically handled by "bumpversion"
        version="0.3.1",
        author="aferro",
        author_email="aferro@em.uni-frankfurt.de",
        description="Qt GUIs for Systems Engineering and Computer Vision",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/andres-fr/secv-guis",
        packages=setuptools.find_packages(exclude=["*utest*"]),
        # dict of package_name: [list_of_patterns]
        # https://stackoverflow.com/a/39823590/4511978
        # package_data={"secv_guis": ["*/*.txt"]},
        include_package_data=True,
        install_requires=REQUIREMENTS,
        classifiers=[
            # comprehensive list: https://pypi.org/classifiers/
            "Programming Language :: Python :: 3 :: Only",
            # "Programming Language :: Python",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent"
        ],
    )


if __name__ == "__main__":
    setup()
