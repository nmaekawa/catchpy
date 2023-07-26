FROM python:3.9
ENV PYTHONUNBUFFERED 1

RUN apt-get update
# Include fortune library for quote generation for text annotations
RUN apt-get install fortune-mod -y
ENV PATH "$PATH:/usr/games"

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN pip install -r catchpy/requirements/local.txt

