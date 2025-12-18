from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy

class FirmRequiredMixin(AccessMixin):
    """Verify that the current user is authenticated AND has a firm."""
    
    def dispatch(self, request, *request_calls, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # If user is logged in but has no firm, send them to the wizard
        if not getattr(request.user, 'firm', None):
            return redirect('users:firm_wizard') # Change this to your actual wizard URL name
            
        return super().dispatch(request, *request_calls, **kwargs)