from django.contrib import admin

from .models import CatchpyProfile, Consumer

# Register your models here.
admin.site.register(Consumer)
admin.site.register(CatchpyProfile)
