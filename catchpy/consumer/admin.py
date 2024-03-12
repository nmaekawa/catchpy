from django.contrib import admin

from catchpy.consumer.models import CatchpyProfile, Consumer

# Register your models here.
admin.site.register(Consumer)
admin.site.register(CatchpyProfile)
