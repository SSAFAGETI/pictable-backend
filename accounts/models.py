from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
import random

ADJECTIVES = ['빠른', '용감한', '신비한', '날쌘', '강력한', '차가운', '뜨거운', '조용한', '영리한', '씩씩한']
NOUNS = ['호랑이', '독수리', '늑대', '용', '사자', '여우', '팬더', '상어', '치타', '매']

def generate_nickname():
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    number = random.randint(100, 999)
    return f"{adj}{noun}{number}"  # 예: 빠른호랑이742

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('이메일은 필수입니다')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
    ]

    email = models.EmailField(unique=True) # email 저장 / 중복 불가
    password_hash = models.CharField(max_length=255) # 비밀번호 hash 값 저장
    nickname = models.CharField(max_length=80, blank=True) # 닉네임 저장
    profile_image_url = models.CharField(max_length=500, blank=True)  # 이미지 URL 저장
    provider = models.CharField(max_length=30, blank=True)  # 이미지 확장자 저장
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='user') # 역할 (user or admin)
    created_at = models.DateTimeField(auto_now_add=True) # 생성된 날짜
    updated_at = models.DateTimeField(auto_now=True) # 수정된 날짜
    deleted_at = models.DateTimeField(null=True, blank=True) # 탈퇴한 날짜 

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def save(self, *args, **kwargs):
        if not self.nickname:  # 닉네임 없을 때만 자동 생성
            self.nickname = generate_nickname()
        if not self.password_hash and self.password:
            self.password_hash = self.password
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.email
    
class OauthAccount(models.Model):
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='oauth_accounts')
    provider         = models.CharField(max_length=30)
    provider_user_id = models.CharField(max_length=255)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('provider', 'provider_user_id')
        
class UserFollow(models.Model):
    follower   = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following')
    following  = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
