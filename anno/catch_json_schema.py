import json
import os


# read api spec from file
here = os.path.abspath(os.path.dirname(__file__))
filepath = os.path.join(here, 'catch_api.json')
with open(filepath, 'r') as f:
    context = f.read()

# extract definitions and tweak to get a json schema for annotation
api_spec = json.loads(context)
jschema = api_spec['definitions']['Annotation'].copy()
jschema['id'] = "http://localhost:8555/catch-annotation.json"
jschema['description'] = "schema for catch webannotations"

definitions = api_spec['definitions']
del(definitions['Annotation'])
jschema['definitions'] = definitions

CATCH_JSON_SCHEMA = jschema
