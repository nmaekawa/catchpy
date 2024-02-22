from django.contrib import admin

from .models import Consumer
from .models import Profile

# Register your models here.
admin.site.register(Consumer)
admin.site.register(Profile)

