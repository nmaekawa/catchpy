from django.contrib import admin

from .models import Anno, Platform, Tag, Target

# Register your models here.
admin.site.register(Anno)
admin.site.register(Platform)
admin.site.register(Tag)
admin.site.register(Target)
