from django.contrib import admin

from .models import Anno, Tag, Target


@admin.register(Anno)
class AnnoAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    list_display = (
        'created', 'anno_id', 'body_format', 'creator_id',
        'anno_reply_to', 'anno_deleted'
    )

# Register your models here.
admin.site.register(Tag)
admin.site.register(Target)
