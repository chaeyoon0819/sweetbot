from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.db import models

# [필수] 유저 생성 및 관리를 담당하는 매니저
class UserManager(BaseUserManager):
    def create_user(self, email, user_id, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email), user_id=user_id)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, user_id, password=None):
        user = self.create_user(email, user_id=user_id, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    name = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField(verbose_name='email', max_length=100, blank=True, null=True, unique=True)
    user_id = models.CharField(max_length=30, blank=True, null=True, unique=True)
    thumbnail = models.CharField(max_length=256, default='default_profile.jpg', blank=True, null=True)
    
    # [필수] 권한 관리를 위한 필드 추가
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)

    # [필수] 위에서 만든 매니저 연결
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['user_id']

    def __str__(self):
        return self.user_id if self.user_id else self.email

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin

    class Meta:
        db_table = 'users'