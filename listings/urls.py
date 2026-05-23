from django.urls import path
from .views import (
    list_categories,
    create_category,
    list_all_listings,
    list_listings_by_category,
    get_listing_detail,
    list_featured_listings,
    create_listing,
    update_listing,
    delete_listing,
    my_listings,
    toggle_save_listing,
    my_saved_listings,
    save_status,
    upload_images,
)

urlpatterns = [
    # ── Categories ──────────────────────────────────────────────────────────
    path('categories/', list_categories, name='list_categories'),
    path('categories/create/', create_category, name='create_category'),

    # ── Public browse ────────────────────────────────────────────────────────
    path('', list_all_listings, name='list_all_listings'),
    path('featured/', list_featured_listings, name='list_featured_listings'),
    path('category/<slug:category_slug>/', list_listings_by_category, name='list_by_category'),
    path('<int:pk>/', get_listing_detail, name='listing_detail'),

    # ── Vendor (owner) CRUD ──────────────────────────────────────────────────
    path('create/', create_listing, name='create_listing'),
    path('<int:pk>/update/', update_listing, name='update_listing'),
    path('<int:pk>/delete/', delete_listing, name='delete_listing'),
    path('my/', my_listings, name='my_listings'),

    # ── Saved / wishlist ─────────────────────────────────────────────────────
    path('save/', toggle_save_listing, name='toggle_save'),
    path('saved/', my_saved_listings, name='my_saved_listings'),
    path('<int:listing_id>/save-status/', save_status, name='save_status'),

    # ── Media upload ─────────────────────────────────────────────────────────
    path('upload/', upload_images, name='upload_images'),
]
