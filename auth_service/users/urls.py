from django.urls import path
from . import views


urlpatterns = [
    path('profile/', views.profile_details, name='profile-details'),
    path('create-user/', views.create_user, name='create-user'),
    path('verify-user/', views.verify_otp, name='verify-user'),
    path('resend-otp/', views.resend_otp, name='resend-otp'),
    path('verify-token/', views.verify_token_microservice, name='verify-token-microservice'),
    path('logout/', views.LogoutView.as_view(), name='logout-user'),
    path('search-by-username/', views.search_by_username, name='search-by-users'),
]


