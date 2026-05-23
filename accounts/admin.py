from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ['phone', 'profile_image', 'latitude', 'longitude', 'custom_location', 'bio']


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ['email', 'first_name', 'last_name', 'is_active', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
