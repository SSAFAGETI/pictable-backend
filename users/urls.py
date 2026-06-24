from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.me, name='me'),
    path('me/saved-recipes/', views.my_saved_recipes, name='my-saved-recipes'),
    path('me/liked-recipes/', views.my_liked_recipes, name='my-liked-recipes'),
    path('me/recipes/', views.my_recipes, name='my-recipes'),
    path('<int:pk>/subscribe/', views.subscribe, name='subscribe'),
    path('me/subscriptions/', views.my_subscriptions, name='my-subscriptions'),
    path('me/subscribers/', views.my_subscribers, name='my-subscribers'),
]