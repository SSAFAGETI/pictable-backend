from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_feed, name='recipe-feed'),
    path('tags/', views.tag_list, name='tag-list'),
]