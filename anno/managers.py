from django.db.models import Manager
from django.db.models import Q


class SearchManager(Manager):
    '''builds Q expression for `platform` annotation property.

    to build a custom search, extend this class and override the
    'search_expression' method.
    '''

    def search_expression(self, params):
        '''builds Q expression for `platform` according to params.'''
        q = Q()

        platform_name = params.get('platform', None)
        if platform_name:
            kwargs = {'raw__platform__platform_name': str(platform_name)}
            q = q & Q(**kwargs)

        context_id = params.get('context_id', None)
        if context_id:
            kwargs = {'raw__platform__context_id': str(context_id)}
            q = q & Q(**kwargs)

            collection_id = params.get('collection_id', None)
            if collection_id:
                kwargs = {'raw__platform__collection_id': str(collection_id)}
                q = q & Q(**kwargs)

        target_source_id = params.get('source_id', None)
        if target_source_id:
            kwargs = {
                'raw__platform__target_source_id': str(target_source_id)}
            q = q & Q(**kwargs)

        return q
