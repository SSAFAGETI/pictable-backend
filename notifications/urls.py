from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification-list'),
    path('<int:pk>/read/', views.notification_read, name='notification-read'),
    path('read-all/', views.notification_read_all, name='notification-read-all'),
]