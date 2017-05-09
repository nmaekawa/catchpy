# -*- coding: utf-8 -*-

class AnnoError(Exception):
    '''generic exception for Annotations.'''


class DuplicateAnnotationIdError(AnnoError):
    '''annotation already exists, cannot create.'''


class InvalidInputWebAnnotationError(AnnoError):
    '''generic exception for semantic errors in WebAnnotation.'''

class InvalidAnnotationBodyTypeError(InvalidInputWebAnnotationError):
    '''type value in body is invalid.'''

class InvalidAnnotationPurposeError(InvalidInputWebAnnotationError):
    '''purpose value in annotation is invalid.'''

class InvalidAnnotationTargetTypeError(InvalidInputWebAnnotationError):
    '''type value of target is invalid.'''

class InvalidTargetMediaTypeError(InvalidInputWebAnnotationError):
    '''media type value of target is invalid.'''

class ParentAnnotationMissingError(InvalidInputWebAnnotationError):
    '''expected reference to parent annotation of comment is missing.'''

class TargetAnnotationForReplyMissingError(InvalidInputWebAnnotationError):
    '''expected target for comment is missing.'''

class MissingAnnotationError(AnnoError):
    '''annotation does not exist.'''
