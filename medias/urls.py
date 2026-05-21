from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.media_upload, name='media-upload'),
    path('<int:pk>/', views.media_detail, name='media-detail'),
]