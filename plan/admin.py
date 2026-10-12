from django.contrib import admin

from .models import Factory, FactoryUser, WorkVolume

admin.site.register(Factory)
admin.site.register(FactoryUser)
admin.site.register(WorkVolume)
