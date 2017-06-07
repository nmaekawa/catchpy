# -*- coding: utf-8 -*-
from datetime import datetime
from datetime import timedelta
import iso8601
import jwt
import logging
import pytz

from .catchjwt import decode_token
from .catchjwt import validate_token
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


        #
        # TODO: refactor into more legible code...
        #

        # get token from request header
        credentials = get_credentials(request)
        if credentials is not None:
            # decode token to get consumerKey
            payload = decode_token(credentials)
            if payload is not None:
                consumer = fetch_consumer(payload)
                if consumer is not None:
                    # validate consumer
                    if not consumer.has_expired():
                        # validate token signature
                        validate_signature = decode_token(
                            credentials, secret_key=consumer.secret_key,
                            verify=True)
                        if validate_signature is not None:
                            # validate token claims
                            error = validate_token(payload)
                            if not error:
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
                        msg = 'consumer({}) has expired'.format(consumer.consumer)
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
            # Work around django test client oddness:
            # https://github.com/jpadilla/django-jwt-auth/blob/master/jwt_auth/utils.py
            if isinstance(header_type, type('')):
                credentials = token.encode('iso-8859-1')
            else:
                credentials = token
    else:       # try annotator header
        header = request.META.get(JWT_ANNOTATOR_HEADER)
        if header:
            credentials = header
            if isinstance(header, type('')):
                credentials = header.encode('iso-8859-1')
            else:
                credentials = header
    return credentials


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



