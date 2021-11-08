catchpy
=======

HarvardX annotations storage API


Overview
--------

catchpy is part of AnnotationsX, HarvardX implementation of annotations using
the `W3C Web Annotation Data Model`_.

The `OpenAPI Specification`_ for the catchpy annotation model can be found at:

    - https://raw.githubusercontent.com/nmaekawa/catchpy/master/anno/static/anno/catch_api.json

A jsonld serialization of this model can be found at:

    - https://catchpy.harvardx.harvard.edu.s3.amazonaws.com/jsonld/catch_context_jsonld.json



Quick Start
-----------

For those who want to quickly check out what catchpy does.

Make sure you have docker_ installed to try this quickstart.

::

    # clone this repo
    $> git clone https://github.com/nmaekawa/catchpy.git
    $> cd catchpy

    # start docker services
    $> docker-compose up
    $> docker-compose exec web python manage.py migrate
    $> docker-compose exec web python manage.py createsupersuser
    $> open http://localhost:8000/static/anno/index.html


This last command opens the API page, where you can try the `Web Annotation`_
and the back-compat AnnotatorJS_ APIs.

To actually issue rest requests, you will need a jwt_ token. Generate one
like below::

    # this generates a consumer/secret api key
    $> docker-compose exec web python manage.py \
            create_consumer_pair \
                --consumer "my_consumer" \
                --secret "super_secret" \
                --expire_in_weeks 1

    # this generates the token that expires in 10 min
    $> docker-compose exec web python manage.py \
            make_token \
                --user "exceptional_user" \
                --api_key "my_consumer" \
                --secret "super_secret" \
                --ttl 3600

The command spits out the token as a long string of chars. Copy that and paste
into the API page, by clicking on the lock at the right of each API call, or on
the ``Authorize`` button at the top right of the page.


Not So Quick Start
------------------

For those who want to set up a local instance of catchpy, for tests or
developement.

Setting up catchpy locally requires:

    - postgres 9.6 or higher
    - python 3.5 or higher

::

    # clone this repo
    $> git clone https://github.com/nmaekawa/catchpy.git
    $> cd catchpy

    # use a virtualenv
    $> virtualenv -p python3 venv
    $> source venv/bin/activate
    (venv) $>  # now using the venv

    # install requirements
    $> (venv) pip install -r catchpy/requirements/dev.txt

    # edit dotenv sample or create your own, db creds etc...
    $> (venv) vi catchpy/settings/sample.env

    # custom django-commands for catchpy have help!
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py --help

    # create the catchpy database
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py migrate

    # create a django-admin user
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py \
            create_user \
                --username "user" \
                --password "password" \
                --is_admin

    # create a consumer key-pair
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py \
            create_consumer_pair \
                --consumer "my_consumer" \
                --secret "super_secret" \
                --expire_in_weeks 1

    # generate a jwt token, the command below expires in 10 min
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py \
            make_token \
                --user "exceptional_user" \
                --api_key "my_consumer" \
                --secret "super_secret" \
                --ttl 3600

    # start the server
    $> (venv) CATCHPY_DOTENV_PATH=path/to/dotenv/file ./manage.py runserver


You probably know this: ``./manage.py runserver`` is **not for production**
deployment, use for development environment only!


Run unit tests
---------------

unit tests require:

    - a postgres 9.6 or higher running (and its config in
      ``catchpy/settings/test.py``); this is hard to fake because it requires
      postgres jsonb data type

    - the fortune program, ex: ``brew install fortune`` if you're in macos.
      ``fortune`` is used to create content in test annotations.

tests are located under each django app:

::

    # tests for annotations
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file pytest -v anno/tests

    # tests for consumer (jwt generation/validation)
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file pytest -v consumer/tests

    # or use tox
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file tox


---eop


.. _W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
.. _OpenAPI Specification: https://swagger.io/specification/v2/
.. _docker: https://www.docker.com
.. _Web Annotation: https://www.w3.org/TR/annotation-model/
.. _AnnotatorJS: http://annotatorjs.org
.. _jwt: https://jwt.io




