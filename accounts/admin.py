from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OauthAccount, User, UserFollow


admin.site.site_header = '찰칵밥상 관리자'
admin.site.site_title = '찰칵밥상 Admin'
admin.site.index_title = '서비스 데이터 관리'


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ('email',)
    list_display = ('email', 'nickname', 'role', 'provider', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'provider', 'is_staff', 'is_active', 'created_at')
    search_fields = ('email', 'nickname', 'profile_image_url')
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    fieldsets = (
        ('계정', {'fields': ('email', 'password')}),
        ('프로필', {'fields': ('nickname', 'profile_image_url', 'provider', 'role', 'deleted_at')}),
        ('권한', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('일시', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (
            '계정 생성',
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2', 'nickname', 'role', 'is_staff', 'is_active'),
            },
        ),
    )
    filter_horizontal = ('groups', 'user_permissions')


@admin.register(OauthAccount)
class OauthAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'provider', 'provider_user_id', 'created_at')
    list_filter = ('provider', 'created_at')
    search_fields = ('user__email', 'provider', 'provider_user_id')
    raw_id_fields = ('user',)
    readonly_fields = ('created_at',)


@admin.register(UserFollow)
class UserFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__email', 'following__email', 'follower__nickname', 'following__nickname')
    raw_id_fields = ('follower', 'following')
    readonly_fields = ('created_at',)
