from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe_list, name='recipe-list'),
    path('<int:pk>/', views.recipe_detail, name='recipe-detail'),
    path('<int:pk>/like/', views.recipe_like, name='recipe-like'),
    path('<int:pk>/save/', views.recipe_save, name='recipe-save'),
    path('ingredients/', views.ingredient_list, name='ingredient-list'),
    path('<int:pk>/comments/', views.comment_list, name='comment-list'),
    path('<int:pk>/comments/<int:comment_pk>/', views.comment_detail, name='comment-detail'),
    path('<int:pk>/comments/<int:comment_pk>/replies/', views.reply_create, name='reply-create'),
]