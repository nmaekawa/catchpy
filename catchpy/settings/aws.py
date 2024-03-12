from catchpy.settings.base import *  # noqa

# The X-Forwarded-Host header should be used in preference to the Host header
# since the app is behind a load balancer.
USE_X_FORWARDED_HOST = True
