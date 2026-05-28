from django.urls import path
from . import views

urlpatterns = [
    path('summary/', views.index, name='index'),
]