FROM python:3.11
ENV PYTHONUNBUFFERED 1

RUN apt-get update

# Include fortune library for quote generation for text annotations
RUN apt-get install fortune-mod -y
ENV PATH "$PATH:/usr/games"

# Install all other versions of Python we want to test with tox
RUN git clone https://github.com/pyenv/pyenv /root/.pyenv
RUN for PYTHON_VERSION in 3.8.19 3.9.19 3.10.14 3.11.9 3.12.3; do \
  set -ex \
    && /root/.pyenv/bin/pyenv install ${PYTHON_VERSION} \
    && /root/.pyenv/versions/${PYTHON_VERSION}/bin/python -m pip install --upgrade pip \
  ; done

# Add to PATH, in order of lowest precedence to highest.
ENV PATH /root/.pyenv/versions/3.8.17/bin:${PATH}
ENV PATH /root/.pyenv/versions/3.9.17/bin:${PATH}
ENV PATH /root/.pyenv/versions/3.10.12/bin:${PATH}
ENV PATH /root/.pyenv/versions/3.12.0b4/bin:${PATH}
ENV PATH /root/.pyenv/versions/3.11.4/bin:${PATH}

RUN mkdir /code
WORKDIR /code
ADD . /code

RUN pip install -r catchpy/requirements/test.txt