from django.urls import path
from .views import list_reviews, create_review, manage_review

urlpatterns = [
    path('<int:listing_id>/', list_reviews, name='list_reviews'),
    path('<int:listing_id>/create/', create_review, name='create_review'),
    path('<int:review_id>/manage/', manage_review, name='manage_review'),
]
