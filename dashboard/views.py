# dashboard/views.py

from django.views.generic import TemplateView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.db.models import Count

# Models from other apps
from scanner.models import ScanResult
from checklists.models import ChecklistSubmission

# Models from current app
from .models import Alert

def public_home(request):
    """
    Landing page for non-logged-in users.
    Redirects to dashboard if already authenticated.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'dashboard/public_home.html')


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        firm = getattr(self.request.user, 'firm', None)
        
        if firm:
            # 1. Get Automated Scans
            recent_scans = ScanResult.objects.filter(firm=firm).order_by('-scan_date')[:5]
            last_scan = recent_scans.first()
            
            # 2. Extract Top Priority Issue
            top_issue = None
            if last_scan:
                vulnerabilities = last_scan.get_vulnerabilities()
                top_issue = next(
                    (v for v in vulnerabilities if str(v.get('severity', '')).upper() in ['HIGH', 'CRITICAL', '8', '9', '10']), 
                    None
                )

            # 3. Manual Audit (Roadmap) Logic - UPDATED TO INCLUDE COUNTS
            last_sub = ChecklistSubmission.objects.filter(firm=firm).order_by('-created_at').first()
            percentage = 0
            total_count = 0      # Initialize variables
            completed_count = 0
            
            if last_sub:
                responses = last_sub.responses.all()
                total_count = responses.count()
                completed_count = responses.exclude(status='pending').count()
                percentage = int((completed_count / total_count) * 100) if total_count > 0 else 0

            context.update({
                'last_scan': last_scan,
                'recent_scans': recent_scans,
                'top_priority_issue': top_issue,
                'submission': last_sub,
                'completion_percentage': percentage,
                'total_count': total_count,          # ADD THIS
                'completed_count': completed_count,  # ADD THIS
                'unread_alerts': Alert.objects.filter(firm=firm, read=False).count(),
            })
        else:
            context.update({
                'recent_scans': [],
                'unread_alerts': 0,
                'completion_percentage': 0,
                'total_count': 0,
                'completed_count': 0,
            })
            
        return context


class AlertListView(LoginRequiredMixin, ListView):
    """
    View to list all security alerts for a firm.
    """
    model = Alert
    template_name = 'dashboard/alerts.html'
    context_object_name = 'alerts'
    paginate_by = 10

    def get_queryset(self):
        # Your models uses 'scan_date' or 'created_at'—matching your logic here:
        return Alert.objects.filter(firm=self.request.user.firm).order_by('-created_at')


class MarkAlertReadView(LoginRequiredMixin, TemplateView):
    """
    Endpoint to mark alerts as read. 
    NOTE: If this is an HTMX/AJAX call that doesn't need a full page, 
    it's better to inherit from 'View' rather than 'TemplateView'.
    """
    template_name = 'dashboard/includes/alert_row.html' # <--- This also needs a template or it will crash

    def post(self, request, pk):
        try:
            alert = Alert.objects.get(pk=pk, firm=request.user.firm)
            alert.read = True
            alert.save()
        except Alert.DoesNotExist:
            pass
        
        # If using HTMX to just update the row, you'd return a specific partial template here.
        # For now, this satisfies the TemplateView requirement:
        return self.render_to_response({'alert': alert})