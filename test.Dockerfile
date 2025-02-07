# pass in Python version as build arg to allow for tests to be run on multiple versions of Python
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}
ENV PYTHONUNBUFFERED 1
ENV PYTHONUNBUFFERED 1

# Include fortune library for quote generation for text annotations
RUN apt-get update && apt-get install -y fortune-mod
ENV PATH "$PATH:/usr/games"

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN pip install -r catchpy/requirements/test.txt