from django.contrib import admin
from .models import CustomUser, CustomUserProfile


class CustomUserAdmin(admin.ModelAdmin):
    model = CustomUser


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(CustomUserProfile)