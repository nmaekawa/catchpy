from datetime import datetime
from datetime import timedelta
import pytest
import pytz
from uuid import uuid4

from django.http import HttpResponse
from django.test import RequestFactory

from ..catchjwt import decode_token
from ..catchjwt import encode_catchjwt
from ..catchjwt import encode_token
from ..catchjwt import validate_token
from ..jwt_middleware import JWT_AUTH_HEADER, JWT_ANNOTATOR_HEADER
from ..jwt_middleware import get_credentials
from ..jwt_middleware import jwt_middleware
from ..models import Consumer


@pytest.mark.django_db
def test_each_function_ok():
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                override=['CAN_UPDATE','CAN_DELETE'])
    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_enc.decode('iso-8859-1'))}
    request = factory.get('/anno', **extra)

    x = get_credentials(request)
    assert x == token_enc

    payload = decode_token(x)
    assert payload['consumerKey'] == c.consumer
    assert payload['userId'] == 'clarice_lispector'
    assert payload['override'] == ['CAN_UPDATE', 'CAN_DELETE']

    payload = decode_token(x, secret_key=c.secret_key, verify=True)
    assert payload is not None

    any_error = validate_token(payload)
    assert any_error is None


@pytest.mark.django_db
def test_middleware_ok():
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                override=['CAN_UPDATE','CAN_DELETE'])
    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_enc.decode('iso-8859-1'))}
    request = factory.get('/anno', **extra)

    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert isinstance(resp, HttpResponse)
    assert request.catchjwt is not None
    assert request.catchjwt['error'] == ''
    assert request.catchjwt['userId'] == 'clarice_lispector'
    assert request.catchjwt['consumer'] == c


@pytest.mark.django_db
def test_middleware_header_missing():
    factory = RequestFactory()
    request = factory.get('/anno')
    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt is not None
    assert request.catchjwt['error'] == ('failed to find auth token in '
                                         'request header')


@pytest.mark.django_db
def test_middleware_invalid_token():
    factory = RequestFactory()
    extra = {JWT_AUTH_HEADER: 'Token 123'}
    request = factory.get('/anno', **extra)
    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    reps = middleware(request)

    assert request.catchjwt is not None
    assert request.catchjwt 

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt is not None
    assert request.catchjwt['error'] == 'failed to decode auth token'
    assert request.catchjwt['userId'] == 'anonymous'


@pytest.mark.django_db
def test_middleware_invalid_consumer():
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey='carmem_miranda',
                                secret=c.secret_key,
                                user='clarice_lispector',
                                override=['CAN_UPDATE','CAN_DELETE'])
    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_enc.decode('iso-8859-1'))}
    request = factory.get('/anno', **extra)

    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt['error'] ==  'invalid consumerKey in auth token'
    assert request.catchjwt['userId'] == 'anonymous'
    assert request.catchjwt['consumerKey'] == ''
    assert 'consumer' not in request.catchjwt


@pytest.mark.django_db
def test_middleware_tampered_token():
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                override=['CAN_UPDATE','CAN_DELETE'])
    token2_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                override=['CAN_UPDATE','CAN_DELETE',
                                          'CAN_ADMIN'])
    (header, payload, signature) = token_enc.decode('iso-8859-1').split('.')
    (header2, payload2, signature2) = token2_enc.decode('iso-8859-1').split('.')
    token_tampered = '.'.join([header2, payload2, signature])

    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_tampered)}
    request = factory.get('/anno', **extra)

    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt['error'] ==  'failed to validate auth token signature'
    assert request.catchjwt['userId'] == 'anonymous'
    assert request.catchjwt['consumerKey'] == ''
    assert 'consumer' not in request.catchjwt


@pytest.mark.django_db
def test_middleware_token_expired():
    date_in_past = datetime.now(pytz.utc) - timedelta(hours=3)
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                iat=date_in_past.isoformat(),
                                ttl=5,
                                override=['CAN_UPDATE','CAN_DELETE'])
    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_enc.decode('iso-8859-1'))}
    request = factory.get('/anno', **extra)

    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt['error'] ==  'token has expired'
    assert request.catchjwt['userId'] == 'anonymous'
    assert request.catchjwt['consumerKey'] == ''
    assert 'consumer' not in request.catchjwt


@pytest.mark.django_db
def test_middleware_issued_in_future():
    date_in_future = datetime.now(pytz.utc) + timedelta(hours=3)
    c = Consumer._default_manager.create()
    token_enc = encode_catchjwt(apikey=c.consumer,
                                secret=c.secret_key,
                                user='clarice_lispector',
                                iat=date_in_future.isoformat(),
                                ttl=5,
                                override=['CAN_UPDATE','CAN_DELETE'])
    factory = RequestFactory()
    extra = {
        JWT_AUTH_HEADER: 'Token {}'.format(token_enc.decode('iso-8859-1'))}
    request = factory.get('/anno', **extra)

    response = HttpResponse('ok')

    def get_response(request):
        return response

    middleware = jwt_middleware(get_response)
    resp = middleware(request)

    assert request.catchjwt['error'] == 'invalid `issuedAt` in the future.'
    assert request.catchjwt['userId'] == 'anonymous'
    assert request.catchjwt['consumerKey'] == ''
    assert 'consumer' not in request.catchjwt



