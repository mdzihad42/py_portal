from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('NSDA Profile', {
            'fields': ('role', 'profile_picture', 'phone', 'bio', 'grade_level', 'school', 'date_of_birth'),
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('NSDA Profile', {
            'fields': ('role', 'email', 'first_name', 'last_name'),
        }),
    )
