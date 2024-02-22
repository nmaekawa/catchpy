from django.urls import resolve
from django.urls import reverse


def match_func_for_url(url):
    func = resolve(url).func
    return func


def test_urls():

    urlconf = [
        #{
        #    'url': '{}?limit=-1'.format(reverse('create_or_search')),
        #    'view_func': 'anno.views.crud_create'},
        #{
        #    'url': '/annos/?context_id=fake-contextID',
        #    'view_func': 'anno.views.create_or_search'},
        {
            'url': '{}?contextId=fake-contextId'.format(
                reverse('compat_search')),
            'view_func': 'anno.views.search_back_compat_api'},
        {
            'url': reverse('compat_create'),
            'view_func': 'anno.views.crud_compat_create'},
        {
            'url': reverse('compat_update', kwargs={'anno_id': '123456789'}),
            'view_func': 'anno.views.crud_compat_update'},
        {
            'url': reverse('compat_delete', kwargs={'anno_id': '123456789'}),
            'view_func': 'anno.views.crud_compat_delete'},
        {
            'url': reverse('compat_destroy', kwargs={'anno_id': '123456789'}),
            'view_func': 'anno.views.crud_compat_delete'},
        {
            'url': reverse('compat_read', kwargs={'anno_id': '123456789'}),
            'view_func': 'anno.views.crud_compat_read'},
        {
            'url': reverse('create_or_search'),
            'view_func': 'anno.views.create_or_search'},
        {
            'url': '/annos/123-456-789',
            'view_func': 'anno.views.crud_api'},
    ]

    for cfg in urlconf:
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&({})'.format(cfg['url']))
        func = match_func_for_url(cfg['url'])
        func_name = '{}.{}'.format(func.__module__, func.__name__)
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&({})'.format(func_name))
        assert func_name == cfg['view_func']
