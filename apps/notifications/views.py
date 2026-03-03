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
class GetNotificationsAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch the latest 30 notifications, BOTH read and unread
        notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:30]
        
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

class MarkAllNotificationsReadAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Find all unread notifications for this user and mark them read
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({"success": True})


class DeleteNotificationAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        # Filter by user to ensure they only delete their own!
        deleted, _ = Notification.objects.filter(id=pk, recipient=request.user).delete()
        if deleted:
            return Response({"success": True})
        return Response({"success": False}, status=404)


class MarkNotificationUnreadAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        Notification.objects.filter(id=pk, recipient=request.user).update(is_read=False)
        return Response({"success": True})