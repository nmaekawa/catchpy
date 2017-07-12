from django.core.urlresolvers import resolve
from django.urls import reverse


def match_func_for_url(url):
    func = resolve(url).func
    return func


def test_urls():

    urlconf = [
        #{
        #    'url': reverse('index'),
        #    'view_func': 'anno.views.index'},
        {
            'url': '{}?contextId=fake-contextId'.format(
                reverse('compat_search')),
            'view_func': 'anno.views.search_back_compat_api'},
        {
            'url': reverse('compat_create'),
            'view_func': 'anno.views.crud_compat_create'},
        {
            'url': reverse('compat_update', kwargs={'anno_id': '123-456-789'}),
            'view_func': 'anno.views.crud_compat_update'},
        {
            'url': reverse('compat_delete', kwargs={'anno_id': '123-456-789'}),
            'view_func': 'anno.views.crud_compat_delete'},
        {
            'url': reverse('crud_create'),
            'view_func': 'anno.views.crud_create'},
        {
            'url': '/annos/?contextId=fake-contextID',
            'view_func': 'anno.views.search_api'},
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
