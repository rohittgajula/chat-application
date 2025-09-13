from django.urls import path
from . import views


urlpatterns = [
    path("protected-test/", views.protected_test, name='protected_test'),
    path("test-auth/", views.test_auth, name='test_auth'),
]
