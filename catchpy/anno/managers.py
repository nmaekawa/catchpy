from django.db.models import Manager
from django.db.models import Q


class SearchManager(Manager):
    '''builds Q expression for `platform` annotation property.

    to build a custom search, extend this class and override the
    'search_expression' method.
    '''

    def search_expression(self, params):
        '''builds Q expression for `platform` according to params.'''
        data = {'platform': {}}
        platform_name = params.get('platform', None)
        if platform_name:
            data['platform']['platform_name'] = platform_name

        context_id = params.get('context_id', None)
        if context_id:
            data['platform']['context_id'] = context_id

        collection_id = params.get('collection_id', None)
        if collection_id:
            data['platform']['collection_id'] = collection_id

        target_source_id = params.get('source_id', None)
        if target_source_id:
            data['platform']['target_source_id'] = target_source_id

        if data['platform']:
            # writing the query like this helps postgres to use indices
            kwargs = {'raw__contains': data}
            q = Q(**kwargs)
        else:
            q = Q()

        return q
