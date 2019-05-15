

from django.http.response import HttpResponseRedirectBase
from django.middleware.common import CommonMiddleware


class HxHttpResponsePermanentRedirectPreserveMethod(HttpResponseRedirectBase):
    status_code = 308


class HxCommonMiddleware(CommonMiddleware):
    """
    redirects with 308 instead of 301.
    308 works as 301 except that it does not allow the client to change the
    request method from POST to GET.

    see:
        https://docs.djangoproject.com/en/2.2/ref/middleware/#django.middleware.common.CommonMiddleware
        https://stackoverflow.com/a/3802178
        https://httpstatuses.com/308
    """

    response_redirect_class = HxHttpResponsePermanentRedirectPreserveMethod


