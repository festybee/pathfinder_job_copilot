"""Re-registers the default User admin with is_active editable directly
from the user list, so approving a pending signup is: open /admin/,
tick the "Active" checkbox on their row, click Save - no need to open
each user's individual edit page."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class ApprovalUserAdmin(UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_staff", "date_joined")
    list_editable = ("is_active",)
    list_filter = ("is_active", "is_staff", "is_superuser", "groups")
    ordering = ("-date_joined",)


admin.site.unregister(User)
admin.site.register(User, ApprovalUserAdmin)
