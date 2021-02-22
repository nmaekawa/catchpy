import json
import os

# read api spec from file
here = os.path.abspath(os.path.dirname(__file__))
filepath = os.path.join(here, 'static/anno/catch_api.json')
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
CATCH_CURRENT_SCHEMA_VERSION = api_spec['info']['version']

# read jsonld from file
jsonld_filepath = os.path.join(here, 'static/anno/catch_context_jsonld.json')
with open(jsonld_filepath, 'r') as f:
    context = f.read()

jsonld_context = json.loads(context)
CATCH_JSONLD_CONTEXT_OBJECT = jsonld_context

#
# TODO: for now this is not very flexible if you need to replace the annotation
# context or schema, since it's reading from files in the package...
# Refactor that into more env_vars if needed.
#
