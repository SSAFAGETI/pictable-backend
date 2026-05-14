from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_list, name='recipe-list'),
    path('<int:pk>/', views.recipe_detail, name='recipe-detail'),
    path('<int:pk>/like/', views.recipe_like, name='recipe-like'),
]