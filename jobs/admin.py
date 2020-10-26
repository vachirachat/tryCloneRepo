from django.contrib import admin
from .models import JobInfo
from .models import JobReservation

admin.site.register(JobInfo)
admin.site.register(JobReservation)
# Register your models here.
# TODO register to admin page
