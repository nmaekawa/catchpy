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
readme = open("README.rst").read()

requirements = [
    "Django",
    "iso8601",
    "jsonschema",
    "psycopg",
    "pyjwt",
    "pyld",
    "python-dateutil",
    "python-dotenv",
    "pytz",
    "requests",
    "django-log-request-id",
    "django-cors-headers",
]

test_requirements = [
    "mock",
    "model_bakery",
    "pytest",
    "pytest-django",
    "pytest-mock",
]


setup(
    name='catchpy',
    version=version,
    description="""Annotation storage backend""",
    long_description=readme,
    author='nmaekawa',
    author_email='nmaekawa@g.harvard.edu',
    url='https://github.com/nmaekawa/catchpy',
    packages=find_packages(exclude=["docs", "tests*"]),
    package_data={
        'anno': ['static/anno/*.json'],
    },
    install_requires=requirements,
    tests_require=test_requirements,
    zip_safe=False,
    keywords='catchpy',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 4.2',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
)
