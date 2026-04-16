from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import traceback


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        try:
            user = super().save_user(request, sociallogin, form)
            return user
        except Exception as e:
            print("SAVE_USER ERROR:", e)
            traceback.print_exc()
            raise

    def is_auto_signup_allowed(self, request, sociallogin):
        return True

    def pre_social_login(self, request, sociallogin):
        print("PRE_SOCIAL_LOGIN called")
        print("User:", sociallogin.user)
        print("Email:", sociallogin.user.email)
        super().pre_social_login(request, sociallogin)