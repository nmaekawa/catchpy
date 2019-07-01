FROM python:3
ENV PYTHONUNBUFFERED 1

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN pip install -r catchpy/requirements/local.txt

