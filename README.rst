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

CatchPy can also be installed a a Django app in an existing Django project. See `below <#install-as-a-django-app>`_ for more details.

Make sure you have docker_ installed to try this quickstart.


::

    # clone this repo
    $> git clone https://github.com/nmaekawa/catchpy.git
    $> cd catchpy

    # start docker services
    $> docker compose up
    $> docker compose exec web python manage.py migrate
    $> docker compose exec web python manage.py createsuperuser
    $> open http://localhost:8000/static/anno/index.html


This last command opens the API page, where you can try the `Web Annotation`_
and the back-compat AnnotatorJS_ APIs.

To actually issue rest requests, you will need a jwt_ token. Generate one
like below::

    # this generates a consumer/secret api key
    $> docker compose exec web python manage.py \
            create_consumer_pair \
                --consumer "my_consumer" \
                --secret "super_secret" \
                --expire_in_weeks 1

    # this generates the token that expires in 10 min
    $> docker compose exec web python manage.py \
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

For those who want to set up a local instance of Catchpy, for tests or
development.

Setting up Catchpy locally requires:

    - Postgres 9.6 or higher
    - Python 3.8 or higher (Django 4.2 requirement)

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

    - Postgres 9.6 or higher (config in
      ``catchpy/settings/test.py``); this is hard to fake because it requires
      postgres jsonb data type

    - the fortune program, ex: ``brew install fortune`` if you're in macos.
      ``fortune`` is used to create content in test annotations.

tests are located under each Django app:

::

    # tests for annotations
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file pytest -v anno/tests

    # tests for consumer (jwt generation/validation)
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file pytest -v consumer/tests

    # or use tox
    CATCHPY_DOTENV_PATH=/path/to/dotenv/file tox


Github Actions CI
---------------
Github Actions is configured to run unit tests on every new PR. The tests are configured in
``.github/workflows/ci-pytest.yml``. The workflow is configured to run tests on Python3.8-3.12 using
``tox``.

---eop


.. _W3C Web Annotation Data Model: https://www.w3.org/TR/annotation-model/
.. _OpenAPI Specification: https://swagger.io/specification/v2/
.. _docker: https://www.docker.com
.. _Web Annotation: https://www.w3.org/TR/annotation-model/
.. _AnnotatorJS: http://annotatorjs.org
.. _jwt: https://jwt.io


Install as a Django app
-----------------------

Add to your `requirements.txt`:

.. code-block:: text

    # Include the latest release from this repository
    https://github.com/artshumrc/catchpy/releases/download/v2.7.1-django-package/catchpy-2.7.0.tar.gz
    Django~=4.2
    iso8601~=2.0.0
    jsonschema==4.18.4
    psycopg>=3.1.8
    PyJWT==2.8.0
    PyLD==2.0.3
    python-dateutil==2.8.2
    python-dotenv==1.0.0
    pytz==2023.3
    requests~=2.31.0
    django-log-request-id==2.1.0
    django-cors-headers~=4.2.0

Add to your `INSTALLED_APPS` in your Django settings:

.. code-block:: python

    INSTALLED_APPS = [
        ...
        'catchpy.anno',
        'catchpy.consumer',
        ...
    ]

Add to your middleware in your Django settings:

.. code-block:: python

    MIDDLEWARE = [
        ...
        'corsheaders.middleware.CorsMiddleware',
        'catchpy.middleware.HxCommonMiddleware',
        'catchpy.consumer.jwt_middleware.jwt_middleware',
        ...
    ]

Add the following to your Django settings:

.. code-block:: python

    # catchpy settings
    CATCH_JSONLD_CONTEXT_IRI = os.environ.get(
        'CATCH_JSONLD_CONTEXT_IRI',
        'http://catchpy.harvardx.harvard.edu.s3.amazonaws.com/jsonld/catch_context_jsonld.json')

    # max number of rows to be returned in a search request
    CATCH_RESPONSE_LIMIT = int(os.environ.get('CATCH_RESPONSE_LIMIT', 200))

    # default platform for annotatorjs annotations
    CATCH_DEFAULT_PLATFORM_NAME = os.environ.get(
        'CATCH_DEFAULT_PLATFORM_NAME', 'hxat-edx_v1.0')

    # admin id overrides all permissions, when requesting_user
    CATCH_ADMIN_GROUP_ID = os.environ.get('CATCH_ADMIN_GROUP_ID', '__admin__')

    # log request time
    CATCH_LOG_REQUEST_TIME = os.environ.get(
        'CATCH_LOG_REQUEST_TIME', 'false').lower() == 'true'
    CATCH_LOG_SEARCH_TIME = os.environ.get(
        'CATCH_LOG_SEARCH_TIME', 'false').lower() == 'true'

    # log jwt and jwt error message
    CATCH_LOG_JWT = os.environ.get(
        'CATCH_LOG_JWT', 'false').lower() == 'true'
    CATCH_LOG_JWT_ERROR = os.environ.get(
        'CATCH_LOG_JWT_ERROR', 'false').lower() == 'true'

    # annotation body regexp for sanity checks
    CATCH_ANNO_SANITIZE_REGEXPS = [
        re.compile(r) for r in ['<\s*script', ]
    ]

    #
    # settings for django-cors-headers
    #
    CORS_ORIGIN_ALLOW_ALL = True   # accept requests from anyone
    CORS_ALLOW_HEADERS = default_headers + (
        'x-annotator-auth-token',  # for back-compat
    )

Add to your Django urls:

.. code-block:: python

    from django.urls import path, include

    from catchpy.urls import urls as catchpy_urls

    urlpatterns = [
        ...
        path("catchpy/", include(catchpy_urls)),
        ...
    ]

Finally, be sure to run migrations.

Build and Package
-----------------

- install `hatch <https://hatch.pypa.io/latest/install/>`_
- set version in ``catchpy/__init__.py``
- package (create Python wheel) ``hatch build``
- publish to PYPI with ``hatch publish``