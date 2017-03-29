from django.contrib import admin

from .models import Batch, College, Semester, Stream, Subject

# Register your models here.

admin.site.register(Batch)
admin.site.register(College)
admin.site.register(Semester)
admin.site.register(Stream)
admin.site.register(Subject)
