# -*- coding:utf-8 -*-


"""
Deploy script for the package. It has to be in the repository root directory.
Make sure that the config entries are correct!
"""

import setuptools


def setup():
    """
    The proper setup function, adapted from the tutorial in
    https://packaging.python.org/tutorials/packaging-projects/
    """
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    with open("README.md", "r") as f:
        long_description = f.read()
    #
    setuptools.setup(
        name="secv_guis",
        # the version is automatically handled by "bumpversion"
        version="0.1.3",
        author="aferro",
        author_email="aferro@em.uni-frankfurt.de",
        description="Qt GUIs for Systems Engineering and Computer Vision",
        long_description=long_description,
        long_description_content_type="text/markdown",
        url="https://github.com/andres-fr/secv-guis",
        packages=setuptools.find_packages(exclude=["*utest*"]),
        # dict of package_name: [list_of_patterns]
        package_data={"secv_guis": ["*/*.txt"]},
        include_package_data=True,
        install_requires=requirements,
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
