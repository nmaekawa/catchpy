FROM python:3.11
ENV PYTHONUNBUFFERED 1

RUN apt-get update

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN pip install -r catchpy/requirements/local.txt

