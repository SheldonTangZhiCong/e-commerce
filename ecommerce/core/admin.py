from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User


class MixinModelAdmin(admin.ModelAdmin):
    empty_value_display = '---'
    exclude = ['created_by', 'modified_by', ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        else:
            obj.modified_by = request.user

        obj.save()


class UserAdminCustom(UserAdmin):
    list_display = ['id', 'date_joined', 'username', 'email', 'first_name', 'last_name', 'profile_type']
    # list_filter = ('is_staff', 'is_superuser')
    search_fields = ('username', 'email')
    ordering = ('-id',)

    def profile_type(self, obj):
        if hasattr(obj, 'visitor'):
            return "Visitor"
        elif hasattr(obj, 'exhibitorprofile'):
            return "Exhibitor"
        else:
            return "N/A"


admin.site.unregister(User)
admin.site.register(User, UserAdminCustom)