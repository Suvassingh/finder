from django.db import models
from django.contrib.auth.models import User


# ─── Category ────────────────────────────────────────────────────────────────

class Category(models.Model):
    """
    Top-level categories: Room, Hotel, Salon, Bus, Restaurant, etc.
    You can add any new type by creating a category via the admin panel
    and optionally adding a new detail model for it.
    """
    CATEGORY_TYPES = [
        ('room', 'Room / Rental'),
        ('hotel', 'Hotel'),
        ('salon', 'Salon / Beauty'),
        ('bus', 'Bus / Transport'),
        ('restaurant', 'Restaurant / Food'),
        ('other', 'Other'),   
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)                          # e.g. 'room', 'hotel'
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='other')
    icon = models.ImageField(upload_to='category_icons/', null=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)               # display order in app

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


# ─── Listing (master table) ──────────────────────────────────────────────────

class Listing(models.Model):
    """
    Core listing shared across ALL category types.
    Extra type-specific fields live in the detail models below.
    Any category using 'other' type works perfectly with just these fields.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Review'),
    ]

    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='listings'
    )
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='listings'
    )

    # Core info
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_label = models.CharField(max_length=100, blank=True)   # e.g. "per night", "per seat"
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)

    # Location
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # Media — stored as list of absolute URLs (uploaded via /api/listings/upload/)
    images = models.JSONField(default=list, blank=True)

    # Meta
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['status', 'is_featured']),
            models.Index(fields=['city']),
        ]

    def __str__(self):
        return f"[{self.category.name}] {self.title}"

    @property
    def average_rating(self):
        agg = self.reviews.aggregate(avg=models.Avg('rating'))
        return round(agg['avg'], 1) if agg['avg'] else None

    @property
    def review_count(self):
        return self.reviews.count()


# ─── Detail models per category type ─────────────────────────────────────────

class RoomDetail(models.Model):
    """Extra fields for Room / Rental listings."""
    ROOM_TYPES = [
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('flat', 'Flat / Apartment'),
        ('shared', 'Shared Room'),
        ('studio', 'Studio'),
        ('house', 'Full House'),
    ]

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='room_detail')
    room_type = models.CharField(max_length=20, choices=ROOM_TYPES, default='single')
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.PositiveIntegerField(default=1)
    floor_area_sqft = models.PositiveIntegerField(null=True, blank=True)
    is_furnished = models.BooleanField(default=False)
    parking_available = models.BooleanField(default=False)
    wifi_available = models.BooleanField(default=False)
    water_included = models.BooleanField(default=False)
    electricity_included = models.BooleanField(default=False)
    available_from = models.DateField(null=True, blank=True)
    min_stay_months = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Room detail — {self.listing.title}"


class HotelDetail(models.Model):
    """Extra fields for Hotel listings."""
    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='hotel_detail')
    star_rating = models.PositiveSmallIntegerField(default=3)    # 1–5
    total_rooms = models.PositiveIntegerField(null=True, blank=True)
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    has_restaurant = models.BooleanField(default=False)
    has_pool = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)
    has_wifi = models.BooleanField(default=True)
    has_parking = models.BooleanField(default=False)
    has_airport_shuttle = models.BooleanField(default=False)
    pet_friendly = models.BooleanField(default=False)
    website = models.URLField(blank=True)

    def __str__(self):
        return f"Hotel detail — {self.listing.title}"


class SalonDetail(models.Model):
    """Extra fields for Salon / Beauty listings."""
    SALON_TYPES = [
        ('unisex', 'Unisex Salon'),
        ('male', 'Male Only'),
        ('female', 'Female Only'),
        ('spa', 'Spa & Wellness'),
        ('nail', 'Nail Studio'),
        ('bridal', 'Bridal Makeup'),
    ]

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='salon_detail')
    salon_type = models.CharField(max_length=20, choices=SALON_TYPES, default='unisex')
    services_offered = models.JSONField(default=list, blank=True)  # ["Haircut", "Massage", ...]
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    open_days = models.JSONField(default=list, blank=True)          # ["Mon", "Tue", ...]
    home_service_available = models.BooleanField(default=False)
    appointment_required = models.BooleanField(default=False)

    def __str__(self):
        return f"Salon detail — {self.listing.title}"


class BusDetail(models.Model):
    """Extra fields for Bus / Transport listings."""
    BUS_TYPES = [
        ('tourist', 'Tourist Bus'),
        ('local', 'Local Bus'),
        ('express', 'Express Bus'),
        ('microbus', 'Microbus'),
        ('private', 'Private Hire'),
        ('night', 'Night Bus'),
    ]

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='bus_detail')
    bus_type = models.CharField(max_length=20, choices=BUS_TYPES, default='local')
    origin = models.CharField(max_length=150)
    destination = models.CharField(max_length=150)
    departure_time = models.TimeField(null=True, blank=True)
    duration_hours = models.FloatField(null=True, blank=True)
    total_seats = models.PositiveIntegerField(null=True, blank=True)
    ac_available = models.BooleanField(default=False)
    wifi_available = models.BooleanField(default=False)
    operates_daily = models.BooleanField(default=True)
    operate_days = models.JSONField(default=list, blank=True)       # if not daily

    def __str__(self):
        return f"Bus — {self.listing.title} ({self.origin} → {self.destination})"


class RestaurantDetail(models.Model):
    """Extra fields for Restaurant / Food listings."""
    CUISINE_CHOICES = [
        ('nepali', 'Nepali'),
        ('chinese', 'Chinese'),
        ('indian', 'Indian'),
        ('continental', 'Continental'),
        ('italian', 'Italian'),
        ('fast_food', 'Fast Food'),
        ('cafe', 'Café'),
        ('bakery', 'Bakery'),
        ('mixed', 'Mixed / Multi-cuisine'),
    ]

    listing = models.OneToOneField(Listing, on_delete=models.CASCADE, related_name='restaurant_detail')
    cuisine_type = models.CharField(max_length=30, choices=CUISINE_CHOICES, default='mixed')
    seating_capacity = models.PositiveIntegerField(null=True, blank=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    open_days = models.JSONField(default=list, blank=True)
    home_delivery = models.BooleanField(default=False)
    takeaway = models.BooleanField(default=True)
    outdoor_seating = models.BooleanField(default=False)
    vegetarian_options = models.BooleanField(default=True)
    vegan_options = models.BooleanField(default=False)
    menu_images = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"Restaurant detail — {self.listing.title}"


# ─── Saved / Wishlist ────────────────────────────────────────────────────────

class SavedListing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_listings')
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'listing')

    def __str__(self):
        return f"{self.user.email} saved {self.listing.title}"


# ─── Image upload tracker ────────────────────────────────────────────────────

class UploadedImage(models.Model):
    """Tracks every uploaded image so orphan cleanup is possible."""
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    image = models.ImageField(upload_to='listing_images/')
    url = models.URLField(blank=True, max_length=500)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.url or str(self.image)
