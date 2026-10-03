from django.contrib import admin
from .models import (
    User,
    Address,
    SocialAccount,
    PasswordResetToken,
    EmailVerificationToken,
)

admin.site.register(User)
admin.site.register(Address)
admin.site.register(SocialAccount)
admin.site.register(PasswordResetToken)
admin.site.register(EmailVerificationToken)