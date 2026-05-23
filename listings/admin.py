from django.contrib import admin
from .models import (
    BusDetail, Category, HotelDetail, Listing,
    RestaurantDetail, RoomDetail, SalonDetail,
    SavedListing, UploadedImage,
)


class RoomDetailInline(admin.StackedInline):
    model = RoomDetail
    can_delete = True
    extra = 0


class HotelDetailInline(admin.StackedInline):
    model = HotelDetail
    can_delete = True
    extra = 0


class SalonDetailInline(admin.StackedInline):
    model = SalonDetail
    can_delete = True
    extra = 0


class BusDetailInline(admin.StackedInline):
    model = BusDetail
    can_delete = True
    extra = 0


class RestaurantDetailInline(admin.StackedInline):
    model = RestaurantDetail
    can_delete = True
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'owner', 'city', 'status', 'is_featured', 'view_count', 'created_at']
    list_filter = ['status', 'is_featured', 'category']
    search_fields = ['title', 'description', 'city', 'owner__email']
    list_editable = ['status', 'is_featured']
    ordering = ['-created_at']
    inlines = [
        RoomDetailInline, HotelDetailInline, SalonDetailInline,
        BusDetailInline, RestaurantDetailInline,
    ]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category_type', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(SavedListing)
admin.site.register(UploadedImage)
