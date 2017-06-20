
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


