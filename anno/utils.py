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
    # originally shifted by 64 to keep number within max integer value
    # but javascript in the frontend support integers with 52bits.
    # https://stackoverflow.com/a/3530326
    # https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Number/MAX_SAFE_INTEGER
    return str(uuid4().int>>76 - 1) if must_be_int else str(uuid4())
