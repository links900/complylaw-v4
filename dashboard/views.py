# dashboard/views.py
from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from scanner.models import ScanResult

from .models import Alert


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        firm = self.request.user.firm
        
        if firm:
            context['recent_scans'] = ScanResult.objects.filter(firm=firm).order_by('-scan_date')[:5]
            context['unread_alerts'] = Alert.objects.filter(firm=firm, read=False).count()
            context['last_scan'] = ScanResult.objects.filter(firm=firm).first()
        else:
            context['recent_scans'] = []
            context['unread_alerts'] = 0
            context['last_scan'] = None
            
        return context

def public_home(request):
    """
    Root URL '/' → Marketing page for non-logged-in users
    Logged-in users → instantly redirected to real dashboard
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')  # → goes to your DashboardView above
    
    return render(request, 'dashboard/public_home.html')
    
    
class AlertListView(LoginRequiredMixin, ListView):
    model = Alert
    template_name = 'dashboard/alerts.html'
    context_object_name = 'alerts'
    paginate_by = 10

    def get_queryset(self):
        return Alert.objects.filter(firm=self.request.user.firm).order_by('-scan_date')


class MarkAlertReadView(LoginRequiredMixin, TemplateView):
    def post(self, request, pk):
        alert = Alert.objects.get(pk=pk, firm=request.user.firm)
        alert.read = True
        alert.save()
        return self.render_to_response({})