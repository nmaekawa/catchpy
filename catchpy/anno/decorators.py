from functools import wraps
from http import HTTPStatus

from django.http import JsonResponse


def require_catchjwt(view_func):
    def _decorator(request, *args, **kwargs):
        # check that middleware added jwt info in request
        catchjwt = getattr(request, "catchjwt", None)
        if catchjwt is None:
            return JsonResponse(
                status=HTTPStatus.UNAUTHORIZED,
                data={
                    "status": HTTPStatus.UNAUTHORIZED,
                    "payload": ["looks like catchjwt middleware is not on"],
                },
            )
        if catchjwt["error"]:
            return JsonResponse(
                status=HTTPStatus.UNAUTHORIZED,
                data={
                    "status": HTTPStatus.UNAUTHORIZED,
                    "payload": [catchjwt["error"]],
                },
            )

        response = view_func(request, *args, **kwargs)
        return response

    return wraps(view_func)(_decorator)
