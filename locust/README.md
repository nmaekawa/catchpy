# catchpy load test

beware that this is the first try to load test catchpy!


    # in the virtualenv for catchpy, install load test requirements
    (catchpy_venv) $> cd catchpy/locust
    (catchpy_venv) $> pip install -r requirements.txt
    
    # edit `locustfile.py` and add consumer pair/key
    ...
    
    # run locustio
    (catchpy_venvs) $> locust --host=http://my-catchpy-under-load-test
    
    # go to http://localhost:8089 and setup the test

# notes

it doesn't make much sense to load test in vagrant boxes but still...
when i tried on my vagrant install, i've got errors when trying to pull the
jsonld context from s3 (things like <urlopen error [Errno -3] Temporary failure
in name resolution>).

