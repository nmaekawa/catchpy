# gunicorn configuration

bind = '0.0.0.0:8000'
workers = 3

# These log settings assume that gunicorn log config will be included in the django base.py logging configuration
accesslog = '-'
errorlog = '-'
access_log_format = '{"request": "%(r)s", "http_status_code": "%(s)s", "http_request_url": "%(U)s", "http_query_string": "%(q)s", "http_verb": "%(m)s", "http_version": "%(H)s", "http_referer": "%(f)s", "x_forwarded_for": "%({x-forwarded-for}i)s", "remote_address": "%(h)s", "request_usec": "%(D)s", "request_sec": "%(L)s"}'