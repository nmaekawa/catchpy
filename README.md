# Annotations Backend

Annotations Backend provides storage for annotations in web annotation format.


# Quick Start

1. add "anno" to your INSTALLED_APPS setting like this:
    
    INSTALLED_APPS = [
        ...
        'anno',
    ]
    
2. include the anno URLconf in your project urls.py like this:
    
    url(r'^anno/', include('anno.urls'))
    
3. Run `python ./manage migrate` to create the annotation models

4. start the development server and visit http://localhost:8000/admnin/ to
   create an annotation

