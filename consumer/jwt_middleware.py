# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import iso8601
import jwt
import logging
import pytz

from .models import Consumer


JWT_AUTH_HEADER = 'HTTP_AUTHORIZATION'
JWT_ANNOTATOR_HEADER = 'HTTP_X_ANNOTATOR_AUTH_TOKEN'

logger = logging.getLogger(__name__)

def jwt_middleware(get_response):

    def middleware(request):
        '''get jwt info into request.'''

        # default anonymous jwt payload
        request.catchjwt = {
            'consumerKey': '',
            'userId': 'anonymous',
            'issuedAt': '',
            'ttl': '',
            'override': [],
        }

        msg = ''

        # get token from request header
        credentials = get_credentials(request)
        if credentials is not None:
            # decode token to get consumerKey
            payload = get_token_payload(credentials)
            if payload is not None:
                consumer = fetch_consumer(payload)
                if consumer is not None:
                    # validate token signature
                    validate_signature = get_token_payload(
                        credentials, verify=True,
                        secret_key=consumer.secret_key)
                    if validate_signature is not None:
                        # validate token claims
                        error = validate_token(payload, consumer)
                        if error:
                            # valid, replace info in request
                            payload['consumer'] = consumer
                            request.catchjwt = payload
                            logger.error(
                                'found profile({}) for consumer({})'.format(
                                    consumer.parent_profile,
                                    consumer.consumer))
                        else:
                            msg = error
                    else:
                        msg = 'failed to validate auth token signature'
                else:
                    msg = 'invalid consumerKey in auth token'
            else:
                msg = 'failed to decode auth token'
        else:
            msg = 'failed to find auth token in request header'

        request.catchjwt['error'] = msg
        if msg:
            logger.warn(msg)

        response = get_response(request)

        # code to be executed for each request/response after
        # the view is called
        return response

    return middleware


def get_credentials(request):
    '''get jwt token from http header.'''
    credentials = None
    header = request.META.get(JWT_AUTH_HEADER, None)
    if header:  # try catchpy header
        (header_type, token) = header.split()
        if header_type.lower() == 'token':
            credentials = token
    else:       # try annotator header
        header = request.META.get(JWT_ANNOTATOR_HEADER)
        if header:
            credentials = header
    return credentials


def get_token_payload(credentials, verify=False, secret_key=''):
    try:    # decode to get consumerKey
        payload = jwt.decode(credentials, secret_key, verify=verify)
    except jwt.exceptions.InvalidTokenError as e:
        logger.info(
            'failed to decode jwt: {}'.format(e), exc_info=True)
        return None
    else:
        return payload


def now_utc():
    return datetime.now(pytz.utc)


def fetch_consumer(token_payload):
    '''get consumer model corresponding to `consumerKey` in token.'''
    consumer_key = token_payload.get('consumerKey', None)
    if consumer_key is None:
        return None

    try:
        consumer = Consumer._default_manager.get(pk=consumer_key)
    except Consumer.DoesNotExist:
        logger.error('invalid consumerKey({}) in auth token'.format(
            consumer_key))
        return None
    else:
        return consumer


def validate_token(token_payload, consumer):
    '''check for token expiration, secret-key expiration.'''

    now = now_utc()

    # check secret-key expiration date
    if consumer.has_expired(now):
        return 'secret key for consumer({}) has expired'.format(
            consumer.consumer)

    # check token expiration date
    issued_at = token_payload.get('issuedAt', None)
    ttl = token_payload.get('ttl', None)
    if issued_at is None or ttl is None:
        return 'missing `issuedAt` or `ttl` in auth token'
    try:
        iat = iso8601.parse_date(issued_at)
        ttl = int(ttl)
    except iso8601.ParseError as e:
        return 'invalid `issuedAt` date format, expected iso8601. {}'.format(e)
    except ValueError:
        return 'invaild `ttl` value, expected integer'

    token_exp = iat + timedelta(seconds=ttl)
    if token_exp < now:
        return 'token has expired'

    # check for issuing at future - trying to cheat expiration?
    if iat > now:
        return 'invalid `issuedAt` in the future.'

    return None

