from rest_framework import serializers, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Notification

# --- Serializer ---
class NotificationSerializer(serializers.ModelSerializer):
    # Format the time nicely for the frontend (e.g., "Oct 24, 2:30 PM")
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'notification_type', 'message', 'link', 'is_read', 'time_ago']

    def get_time_ago(self, obj):
        return obj.created_at.strftime("%b %d, %I:%M %p")

# --- Views ---
class UnreadNotificationsAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch the 10 most recent unread notifications
        notifications = Notification.objects.filter(
            recipient=request.user, 
            is_read=False
        ).order_by('-created_at')[:10]
        
        serializer = NotificationSerializer(notifications, many=True)
        return Response({
            "count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
            "notifications": serializer.data
        })

class MarkNotificationReadAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({"success": True})