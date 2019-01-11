#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re

from setuptools import setup
from setuptools import find_packages


def get_version(*file_paths):
    """Retrieves the version from annotation/__init__.py"""
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    version_file = open(filename).read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


version = get_version("catchpy", "__init__.py")

readme = open('README.md').read()
history = open('HISTORY.md').read().replace('.. :changelog:', '')

requirements = [
    "Django",
    "python-dotenv",
    "psycopg2",
]

test_requirements = [
    "mock",
    "model_mommy",
    "pytest",
    "pytest-django",
    "pytest-mock",
]


setup(
    name='catchpy',
    version=version,
    description="""Annotation storage backend""",
    long_description=readme + '\n\n' + history,
    author='nmaekawa',
    author_email='nmaekawa@g.harvard.edu',
    url='https://github.com/nmaekawa/catchpy',
    packages=find_packages(exclude=["docs", "tests*"]),
    include_package_data=True,
    install_requires=requirements,
    tests_require=test_requirements,
    zip_safe=False,
    keywords='catchpy',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
)
