# -*- coding: utf-8 -*-
from http import HTTPStatus


class AnnoError(Exception):
    '''generic exception for Annotations.'''
    status = HTTPStatus.INTERNAL_SERVER_ERROR  # 500

class DuplicateAnnotationIdError(AnnoError):
    '''annotation already exists, cannot create.'''
    status = HTTPStatus.CONFLICT  # 409

class InvalidInputWebAnnotationError(AnnoError):
    '''generic exception for semantic errors in WebAnnotation.'''
    status = HTTPStatus.BAD_REQUEST  # 400

class InvalidAnnotationBodyTypeError(InvalidInputWebAnnotationError):
    '''type value in body is invalid.'''
    status = HTTPStatus.UNPROCESSABLE_ENTITY  # 422

class InvalidAnnotationCreatorError(AnnoError):
    '''annotation creator does not match requesting user.'''
    status = HTTPStatus.CONFLICT  # 409

class InvalidAnnotationPurposeError(InvalidInputWebAnnotationError):
    '''purpose value in annotation is invalid.'''
    status = HTTPStatus.UNPROCESSABLE_ENTITY  # 422

class InvalidAnnotationTargetTypeError(InvalidInputWebAnnotationError):
    '''type value of target is invalid.'''
    status = HTTPStatus.UNPROCESSABLE_ENTITY  # 422

class InvalidTargetMediaTypeError(InvalidInputWebAnnotationError):
    '''media type value of target is invalid.'''
    status = HTTPStatus.UNPROCESSABLE_ENTITY  # 422

class ParentAnnotationMissingError(InvalidInputWebAnnotationError):
    '''expected reference to parent annotation of comment is missing.'''
    status = HTTPStatus.CONFLICT  # 409

class TargetAnnotationForReplyMissingError(InvalidInputWebAnnotationError):
    '''expected target for comment is missing.'''
    status = HTTPStatus.CONFLICT  # 409

class MissingAnnotationError(AnnoError):
    '''annotation does not exist.'''
    status = HTTPStatus.NOT_FOUND  # 404

class MissingAnnotationInputError(AnnoError):
    '''annotation information not present in http request, cannot create obj.'''
    status = HTTPStatus.BAD_REQUEST  # 400

class MissingAnnotationCreatorInputError(AnnoError):
    '''annotation creator not present in http request, cannot create obj.'''
    status = HTTPStatus.BAD_REQUEST  # 400

class NoPermissionForOperationError(AnnoError):
    status = HTTPStatus.FORBIDDEN  # 403


class AnnotatorJSError(AnnoError):
    '''annotatorjs is malformed or not possible to format.'''
    status = HTTPStatus.BAD_REQUEST

class RawModelOutOfSynchError(AnnoError):
    '''raw json and model are out of synch: corrupted data!'''
    status = HTTPStatus.INTERNAL_SERVER_ERROR  # 500


class UnknownOutputFormatError(AnnoError):
    '''output error not catch-webannotation nor annotatorjs.'''
    status = HTTPStatus.BAD_REQUEST
