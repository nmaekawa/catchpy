Annotations Backend CATCHpy/CATCHv2
===================

annotations backend provides storage api for annotations in Catch WebAnnotation
format.

for info on Catch WebAnnotation, check:

- https://catchpy.harvardx.harvard.edu.s3.amazonaws.com/api/catch_api.json
- https://catchpy.harvardx.harvard.edu.s3.amazonaws.com/jsonld/catch_context_jsonld.json



vagrant quick start
===================

this will start 2 ubuntu 16.04 instances: one for postgres other for catchpy
django app.

you will need

- ansible provisioning repo dir at the same level as catchpy dir
- vagrant with landrush plugin (for dns)
    - `vagrant plugin install landrush`
- virtualbox
- ansible

step-by-step
------------

    # clone catchpy and catchpy-provision
    git clone https://github.com/nmaekawa/catchpy-provision.git
    git clone https://github.com/nmaekawa/catchpy.git
    
    # start vagrant instances
    cd catchpy
    vagrant up
    
    # provision both instances
    ansible-playbook -i provision/hosts/vagrant.ini --private-key \
        ~/.vagrant.d/insecure_private_key provision/playbook.yml
    
    # now go to a browser and access http://catchpy.vm/static/anno/index.html
    # this will present a nice interface for the catchpy api
    # note that, for vagrant, nginx is configured to serve content via HTTP;
    # and in prod, via HTTPS.


more info on provisioning
-------------------------

check readme from catchpy-provisioning repo at
https://github.com/nmaekawa/catchpy-provision


to play with this catchpy install
---------------------------------

you can use the default api key-pair created for the django admin user; check
the table `consumer` in the django admin ui (or use `psql`, catchpy:catchpy).
The default django admin user is dragonman:password.

the easiest way to generate an encoded token is to grab the key-pair from the
django admin user and paste it to http://jwt.io debugger.

first, paste the secret-key in the "verify signature" tab of jwt.io (the bottom
one, in blue).

then the payload must be something like:

    {
      "consumerKey": "the-consumer-key-from-django-admin-user",
      "userId": "some-dummy-user-id",
      "issuedAt": "YYYY-MM-DDTHH:mm:SS+00:00",
      "ttl": 6000
    }

the encoded token will show up in the left part of the screen.



development
===========

2 ways to work in catchpy development: in vagrant catchpy.vm instance or
setting a local installation of catchpy.

> i've tried to set a symlink to `/vagrant` shared folder under the catchpy
> install dir, but had problems with user `catchpy` writing to it while
> pip installing catchpy as an editable package. if you figure this out, let me
> know!


working on catchpy.vm instance
------------------------------

login as vagrant user and sudo as catchpy. You might want to make catchpy a
sudoer.

    # in host box, ssh into catchpy.vm instance
    host> vagrant ssh catchpy
    # or
    host> ssh -i ~/.vagrant.d/insecure_private_key vagrant@catchpy.vm
    
    # in catchpy.vm, stop catchpy/gunicorn service
    catchpy> sudo supervisorctl stop catchpy
    
    # then become catchpy user
    catchpy> sudo su catchpy
    
    # start venv
    catchpy> source /opt/hx/catchpy/venvs/catchpy/bin/activate
    
    # go to catchpy clone
    (catchpy) catchpy> cd /opt/hx/catchpy/catchpy
    
    # you can start catchpy
    (catchpy) catchpy> ./manage.py runserver 0.0.0.0:8000

beware that to start catchpy with `manage.py` you have to have the
`CATCHPY_DOTENV_PATH` defined. This path has env vars definitions for the
django app to run.


working on a local catchpy installation
---------------------------------------

you're going to need a postgres 9.6 server running; you can install it locally
via preferred method, use a docker container, or use the vagrant postgres.vm
vagrant instance.

catchpy requires _python3_: 3.5 or higher

     # clone repo
     git clone https://github.com/nmaekawa/catchpy.git
     
     # create venv
     cd catchpy
     virtualenv -p python3 venv
     
     # install requirements
     source catchpy/bin/activate
     (venv) pip install -r requirements/dev.txt
     
     # edit dotenv sample or create your own, db creds etc...
     (venv) vi catchpy/settings/sample.env
     
     # set env var pointing to dotenv file
     (venv) export CATCHPY_DOTENV_PATH=<path/to/catchpy/repo>/catchpy/settings/sample.env
     
     # now you can start the server
     (venv) ./manage.py runserver


run unit tests
--------------

unit tests require a db running (and its config in `catchpy/settings/test.py`)
and are located under each django app:

    # tests for annotations
    py.test anno/tests
    
    # tests for consumer (jwt generation/validation)
    py.test consumer/tests
    

