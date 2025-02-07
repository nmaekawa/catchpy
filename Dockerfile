FROM python:3.12
ENV PYTHONUNBUFFERED 1

RUN apt-get update

RUN mkdir /code
WORKDIR /code
ADD . /code

ARG REQUIREMENTS_FILE=catchpy/requirements/local.txt

RUN pip install -r ${REQUIREMENTS_FILE}
