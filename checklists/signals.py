@#checklists\signals.py
receiver(pre_save, sender=ChecklistResponse)
def log_audit_change(sender, instance, **kwargs):
    if instance.pk:
        old_val = ChecklistResponse.objects.get(pk=instance.pk).status
        if old_val != instance.status:
            print(f"AUDIT LOG: Control {instance.template.code} changed from {old_val} to {instance.status} by {instance.submission.completed_by}")