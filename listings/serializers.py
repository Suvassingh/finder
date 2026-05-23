from rest_framework import serializers
from django.contrib.auth.models import User

from .models import (
    BusDetail,
    Category,
    HotelDetail,
    Listing,
    RestaurantDetail,
    RoomDetail,
    SalonDetail,
    SavedListing,
    UploadedImage,
)


# ─── Category ────────────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    listing_count = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'category_type', 'icon',
            'description', 'order', 'listing_count',
        ]

    def get_listing_count(self, obj):
        return obj.listings.filter(status='active').count()

    def get_icon(self, obj):
        request = self.context.get('request')
        if obj.icon:
            if request:
                return request.build_absolute_uri(obj.icon.url)
            return obj.icon.url
        return None


# ─── Detail serializers ───────────────────────────────────────────────────────

class RoomDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDetail
        exclude = ['id', 'listing']


class HotelDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HotelDetail
        exclude = ['id', 'listing']


class SalonDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalonDetail
        exclude = ['id', 'listing']


class BusDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusDetail
        exclude = ['id', 'listing']


class RestaurantDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantDetail
        exclude = ['id', 'listing']


# ─── Listing (read — full detail) ─────────────────────────────────────────────

class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email']


class ListingSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    owner = OwnerSerializer(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)

    # Detail blocks — null when not applicable to the listing's category
    room_detail = RoomDetailSerializer(read_only=True)
    hotel_detail = HotelDetailSerializer(read_only=True)
    salon_detail = SalonDetailSerializer(read_only=True)
    bus_detail = BusDetailSerializer(read_only=True)
    restaurant_detail = RestaurantDetailSerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'owner', 'category',
            'title', 'description', 'price', 'price_label',
            'contact_phone', 'contact_email', 'whatsapp',
            'address', 'city', 'latitude', 'longitude',
            'images', 'status', 'is_featured',
            'view_count', 'average_rating', 'review_count',
            'created_at', 'updated_at',
            # detail blocks (null if this listing's category doesn't use them)
            'room_detail', 'hotel_detail', 'salon_detail',
            'bus_detail', 'restaurant_detail',
        ]


# ─── Listing (read — minimal card for list views) ────────────────────────────
class ListingMinimalSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    thumbnail = serializers.SerializerMethodField()
    owner = OwnerSerializer(read_only=True)

    class Meta:
        model = Listing
        fields = [
            'id', 'owner', 'title', 'price', 'price_label', 'city',
            'address', 'contact_phone', 'latitude', 'longitude',  
            'images', 'category_name', 'category_slug', 'thumbnail', 'is_featured',
            'average_rating', 'review_count', 'view_count', 'created_at',
        ]

    def get_thumbnail(self, obj):
        return obj.images[0] if obj.images else None

# ─── Listing (write — create & update) ───────────────────────────────────────

class ListingCreateSerializer(serializers.ModelSerializer):
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )

    # Optional detail blocks — send only the one matching the listing's category
    room_detail = RoomDetailSerializer(required=False)
    hotel_detail = HotelDetailSerializer(required=False)
    salon_detail = SalonDetailSerializer(required=False)
    bus_detail = BusDetailSerializer(required=False)
    restaurant_detail = RestaurantDetailSerializer(required=False)

    class Meta:
        model = Listing
        fields = [
            'category_id',
            'title', 'description', 'price', 'price_label',
            'contact_phone', 'contact_email', 'whatsapp',
            'address', 'city', 'latitude', 'longitude',
            'images',
            # detail blocks
            'room_detail', 'hotel_detail', 'salon_detail',
            'bus_detail', 'restaurant_detail',
        ]

    def create(self, validated_data):
        room_data = validated_data.pop('room_detail', None)
        hotel_data = validated_data.pop('hotel_detail', None)
        salon_data = validated_data.pop('salon_detail', None)
        bus_data = validated_data.pop('bus_detail', None)
        restaurant_data = validated_data.pop('restaurant_detail', None)

        listing = Listing.objects.create(**validated_data)

        if room_data:
            RoomDetail.objects.create(listing=listing, **room_data)
        if hotel_data:
            HotelDetail.objects.create(listing=listing, **hotel_data)
        if salon_data:
            SalonDetail.objects.create(listing=listing, **salon_data)
        if bus_data:
            BusDetail.objects.create(listing=listing, **bus_data)
        if restaurant_data:
            RestaurantDetail.objects.create(listing=listing, **restaurant_data)

        return listing

    def update(self, instance, validated_data):
        room_data = validated_data.pop('room_detail', None)
        hotel_data = validated_data.pop('hotel_detail', None)
        salon_data = validated_data.pop('salon_detail', None)
        bus_data = validated_data.pop('bus_detail', None)
        restaurant_data = validated_data.pop('restaurant_detail', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        def _upsert(detail_attr, model_class, data):
            if data is None:
                return
            detail_obj = getattr(instance, detail_attr, None)
            if detail_obj:
                for attr, value in data.items():
                    setattr(detail_obj, attr, value)
                detail_obj.save()
            else:
                model_class.objects.create(listing=instance, **data)

        _upsert('room_detail', RoomDetail, room_data)
        _upsert('hotel_detail', HotelDetail, hotel_data)
        _upsert('salon_detail', SalonDetail, salon_data)
        _upsert('bus_detail', BusDetail, bus_data)
        _upsert('restaurant_detail', RestaurantDetail, restaurant_data)

        return instance


# ─── Saved listings ───────────────────────────────────────────────────────────

class SavedListingSerializer(serializers.ModelSerializer):
    listing = ListingMinimalSerializer(read_only=True)

    class Meta:
        model = SavedListing
        fields = ['id', 'listing', 'saved_at']


# ─── Image upload ─────────────────────────────────────────────────────────────

class UploadedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedImage
        fields = ['id', 'url', 'uploaded_at']
