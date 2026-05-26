from django.contrib import admin

from notifications.utils import send_push_notification
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
    def save_model(self, request, obj, form, change):
        # Check if this is an update and the featured flag changed
        if change:
            original = Listing.objects.get(pk=obj.pk)
            if not original.is_featured and obj.is_featured:
                # Featured just turned on → notify owner
                send_push_notification(
                    obj.owner,
                    "Your listing is now featured!",
                    f"'{obj.title}' is now featured and will appear prominently.",
                    data={'listing_id': obj.id}
                )
        super().save_model(request, obj, form, change)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category_type', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}


admin.site.register(SavedListing)
admin.site.register(UploadedImage)
