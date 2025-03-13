# users/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from rest_framework import generics

from .models import User
from .serializers import (
    SellerRegistrationSerializer,
    DriverRegistrationSerializer,
    LoginSerializer,
    UserSerializer
)
from mainapp.permissions import IsAdmin

class SellerRegistrationView(APIView):
    """
    API endpoint for seller registration.
    Expects fields: username, email, password, first_name, last_name, phone, city.
    The role is automatically set to 'seller'.
    """
    def post(self, request):
        serializer = SellerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # Serialize the created user (excluding sensitive data)
            user_serializer = UserSerializer(user)
            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DriverRegistrationView(APIView):
    """
    API endpoint for driver registration.
    Expects similar fields to seller registration. The role is automatically set to 'driver'.
    """
    def post(self, request):
        serializer = DriverRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user_serializer = UserSerializer(user)
            return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        try:
            # Find user by email instead of username
            user = User.objects.get(email=email)
            # Authenticate with the found username
            auth_user = authenticate(username=user.username, password=password)
            
            if auth_user:
                if not auth_user.approved and auth_user.role != 'admin':
                    return Response({"error": "User not approved by admin."},
                                status=status.HTTP_403_FORBIDDEN)
                
                token, created = Token.objects.get_or_create(user=auth_user)
                return Response({
                    "token": token.key,
                    "user": UserSerializer(auth_user).data
                }, status=status.HTTP_200_OK)
            
            return Response({"error": "Invalid credentials"}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        except User.DoesNotExist:
            return Response({"error": "No user found with this email"}, 
                          status=status.HTTP_401_UNAUTHORIZED)


class UserProfileView(APIView):
    """
    API endpoint for retrieving and updating the current user's profile.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            # Don't allow changing role or approval status via this endpoint
            if 'role' in serializer.validated_data:
                del serializer.validated_data['role']
            if 'approved' in serializer.validated_data:
                del serializer.validated_data['approved']
                
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApproveUserView(APIView):
    """
    API endpoint for admins to approve users.
    Only admins can access this endpoint.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def patch(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        user.approved = True
        user.save()
        
        return Response(UserSerializer(user).data)

# Add this to users/views.py
class UserListView(generics.ListAPIView):
    """
    API endpoint for listing users.
    GET: Admin can see all users, sellers and drivers can see only themselves.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return User.objects.all()
        # Other users can only see themselves
        return User.objects.filter(id=user.id)
    
class DebugView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'username': user.username,
            'role': user.role,
            'is_authenticated': user.is_authenticated,
            'approved': user.approved,
            'user_id': user.id,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        })
    
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint for admins to manage users.
    GET: Retrieve a specific user
    PUT/PATCH: Update user details
    DELETE: Delete a user
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]