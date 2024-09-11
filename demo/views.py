from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from .models import User, FriendRequest
from .serializers import UserSerializer, FriendRequestSerializer
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import UserRateThrottle

class SignUpView(generics.CreateAPIView):
    serializer_class = UserSerializer

class LoginView(generics.GenericAPIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        try:
            user = authenticate(email=email, password=password)
            if user:
                return Response({"message": "Login successful" })
            return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SearchUsersView(generics.ListAPIView):
    serializer_class = UserSerializer
    pagination_class = PageNumberPagination

    def get_queryset(self):
        search_term = self.request.query_params.get('q')

        # If search term matches an email exactly, return the user with that email
        if User.objects.filter(email__iexact=search_term).exists():
            return User.objects.filter(email__iexact=search_term)

        # Otherwise, return users where the name contains the search term
        return User.objects.filter(name__icontains=search_term)


class FriendRequestThrottle(UserRateThrottle):
    rate = '3/min'

class SendFriendRequestView(generics.CreateAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [FriendRequestThrottle]

    def post(self, request):
        from_user = request.user
        to_user_email = request.data.get("to_user")
        to_user = User.objects.get(email=to_user_email)
        friend_request, created = FriendRequest.objects.get_or_create(from_user=from_user, to_user=to_user)
        if created:
            return Response({"message": "Friend request sent"})
        return Response({"error": "Friend request already exists"}, status=status.HTTP_400_BAD_REQUEST)

class ListFriendsView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.friends.all()

class PendingFriendRequestsView(generics.ListAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return FriendRequest.objects.filter(to_user=self.request.user, status='pending')

class AcceptRejectFriendRequestView(generics.UpdateAPIView):
    serializer_class = FriendRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        
        try:
            user_from = User.objects.get(email=request.data.get('from_user'))
            friend_request = FriendRequest.objects.get(to_user=request.user, from_user=user_from)
        except Exception as e:
            return Response({"error": str(e)})
        
        status = request.data.get("status")
        if status in ['accepted', 'rejected']:
            if status == 'accepted':
                friend_request.from_user.friends.add(friend_request.to_user)
                friend_request.to_user.friends.add(friend_request.from_user)

            friend_request.status = status
            friend_request.save()

            return Response({"message": f"Friend request {status}"})
        return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
