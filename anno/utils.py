from uuid import uuid4

def string_to_number(text):
    '''try to convert string to int or float.

    if failure, return same string
    '''
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return text


def generate_uid(must_be_int=False):
    ''' for backward-compat, generate id as integer.'''
    return str(uuid4().int>>64) if must_be_int else str(uuid4())
