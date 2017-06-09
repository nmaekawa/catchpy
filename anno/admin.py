from django.contrib import admin

from .models import Anno, Tag, Target

# Register your models here.
admin.site.register(Anno)
admin.site.register(Tag)
admin.site.register(Target)
