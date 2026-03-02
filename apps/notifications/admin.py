from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    # Columns displayed in the main list view
    list_display = ('id', 'recipient', 'notification_type', 'message', 'is_read', 'created_at')
    
    # Filter sidebar for quick sorting
    list_filter = ('is_read', 'notification_type', 'created_at')
    
    # Allows searching by the recipient's username or the message content
    search_fields = ('recipient__username', 'recipient__email', 'message')
    
    # Performance optimization to prevent N+1 database query issues
    list_select_related = ('recipient',)
    
    # Make created_at read-only so it can be viewed inside the detail page
    readonly_fields = ('created_at',)
    
    # Date drill-down navigation at the top
    date_hierarchy = 'created_at'