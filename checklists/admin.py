from django.contrib import admin
from .models import ChecklistTemplate, ChecklistSubmission, ChecklistResponse, EvidenceFile
from django.contrib import admin
from .models import ScanResult

@admin.register(ChecklistTemplate)
class ChecklistTemplateAdmin(admin.ModelAdmin):
    list_display = ('standard', 'code', 'title', 'risk_impact', 'active')
    list_filter = ('standard', 'risk_impact', 'active')
    search_fields = ('code', 'title', 'description')
    ordering = ('standard', 'code')

class ChecklistResponseInline(admin.TabularInline):
    model = ChecklistResponse
    extra = 0
    readonly_fields = ('template', 'status', 'comment')

@admin.register(ChecklistSubmission)
class ChecklistSubmissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'scan', 'firm', 'created_at', 'is_locked')
    list_filter = ('is_locked', 'created_at')
    inlines = [ChecklistResponseInline]

@admin.register(EvidenceFile)
class EvidenceFileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'response', 'uploaded_by', 'uploaded_at')
    
    


@admin.register(ScanResult)
class ScanResultAdmin(admin.ModelAdmin):
    # This makes the UUID and key info visible in the list view
    list_display = ('id', 'domain', 'firm', 'scan_date', 'status', 'progress')
    list_filter = ('status', 'scan_date')
    search_fields = ('domain', 'id')
    readonly_fields = ('id', 'scan_date') # IDs are read-only