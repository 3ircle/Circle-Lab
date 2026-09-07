from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from .forms import LoginForm


class UserLoginView(LoginView):
    template_name = 'user_module/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return super().get_success_url() or reverse_lazy('index-page')


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login')
