from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView


@method_decorator(ensure_csrf_cookie, name='dispatch')
class LoginPageView(TemplateView):
    template_name = 'ui/login.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class DashboardPageView(TemplateView):
    template_name = 'ui/dashboard.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class TicketsPageView(TemplateView):
    template_name = 'ui/tickets.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class NewTicketPageView(TemplateView):
    template_name = 'ui/new_ticket.html'


@method_decorator(ensure_csrf_cookie, name='dispatch')
class TicketDetailPageView(TemplateView):
    template_name = 'ui/ticket_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ticket_id'] = int(kwargs['pk'])
        return context


def _page(template):
    @method_decorator(ensure_csrf_cookie, name='dispatch')
    class Page(TemplateView):
        template_name = template
    return Page


ForgotPasswordPageView = _page('ui/forgot_password.html')
ResetPasswordPageView = _page('ui/reset_password.html')
RegisterPageView = _page('ui/register.html')
ProfilePageView = _page('ui/profile.html')
ManageUsersPageView = _page('ui/admin_users.html')
ManageSetupPageView = _page('ui/admin_setup.html')
ManageSettingsPageView = _page('ui/admin_settings.html')
