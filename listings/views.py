import os
from datetime import datetime

from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import F, Q

from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Category, Listing, SavedListing, UploadedImage
from .serializers import (
    CategorySerializer,
    ListingCreateSerializer,
    ListingMinimalSerializer,
    ListingSerializer,
    SavedListingSerializer,
)
from django.db.models import F, Q, FloatField
from django.db.models.functions import Radians, Cos, Sin, ATan2, Sqrt
def _annotate_distance(qs, lat, lng):
    """
    Annotate each row with 'distance_km' (computed using the Haversine formula).
    Returns the annotated queryset.
    """
    # Convert latitude and longitude to radians
    lat_rad = Radians(lat)
    lng_rad = Radians(lng)

    # Convert listing's coordinates to radians
    listing_lat_rad = Radians(F('latitude'))
    listing_lng_rad = Radians(F('longitude'))

    # Difference in coordinates
    dlat = listing_lat_rad - lat_rad
    dlng = listing_lng_rad - lng_rad

    # Haversine formula
    a = (Sin(dlat / 2) ** 2 +
         Cos(lat_rad) * Cos(listing_lat_rad) *
         (Sin(dlng / 2) ** 2))
    c = 2 * ATan2(Sqrt(a), Sqrt(1 - a))
    distance = 6371 * c   # Earth radius in km

    return qs.annotate(distance_km=distance)
# ─── Helpers ─────────────────────────────────────────────────────────────────

def _paginate(queryset, request, serializer_class, context=None):
    """Simple page-based pagination helper."""
    try:
        page = max(1, int(request.GET.get('page', 1)))
        page_size = min(int(request.GET.get('page_size', 20)), 50)
    except (ValueError, TypeError):
        page, page_size = 1, 20

    total = queryset.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = queryset[start:end]

    ctx = {'request': request}
    if context:
        ctx.update(context)

    return Response({
        'count': total,
        'page': page,
        'page_size': page_size,
        'total_pages': max(1, (total + page_size - 1) // page_size),
        'results': serializer_class(items, many=True, context=ctx).data,
    })


def _apply_listing_filters(qs, params):
    """Apply search, filter, and sort from query params."""
    # Full-text search
    q = params.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(description__icontains=q) |
            Q(city__icontains=q) |
            Q(address__icontains=q)
        )

    # City filter
    city = params.get('city', '').strip()
    if city:
        qs = qs.filter(city__icontains=city)

    # Price range
    min_price = params.get('min_price')
    max_price = params.get('max_price')
    if min_price:
        try:
            qs = qs.filter(price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=float(max_price))
        except ValueError:
            pass

    # Featured only
    if params.get('featured') in ('true', '1'):
        qs = qs.filter(is_featured=True)

    # Sort
    sort_map = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price_low': 'price',
        'price_high': '-price',
        'popular': '-view_count',
    }
    sort_key = params.get('sort', 'newest')
    qs = qs.order_by(sort_map.get(sort_key, '-created_at'))

    return qs


# ─── Categories ──────────────────────────────────────────────────────────────

@api_view(['GET'])
def list_categories(request):
    """List all active categories."""
    categories = Category.objects.filter(is_active=True)
    return Response(CategorySerializer(categories, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_category(request):
    """Admin-only: create a new category."""
    if not request.user.is_staff:
        return Response({"error": "Admin access required."}, status=403)

    serializer = CategorySerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


# ─── Listings — public browse ─────────────────────────────────────────────────

@api_view(['GET'])
def list_all_listings(request):
    """
    Browse all active listings.
    Query params: q, city, min_price, max_price, featured, sort, page, page_size,
                  lat, lng, radius (km)
    """
    qs = Listing.objects.filter(status='active').select_related('category', 'owner')

    # --- Distance filtering (if lat, lng, radius are provided) ---
    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
        radius = float(request.GET.get('radius', ''))
    except (TypeError, ValueError):
        lat = lng = radius = None

    if lat is not None and lng is not None and radius is not None and radius > 0:
        # Only listings that have coordinates
        qs = qs.filter(latitude__isnull=False, longitude__isnull=False)
        # Annotate distance and filter within radius
        qs = _annotate_distance(qs, lat, lng)
        qs = qs.filter(distance_km__lte=radius).order_by('distance_km')
    else:
        # No distance filter – apply normal search & sort
        qs = _apply_listing_filters(qs, request.GET)

    return _paginate(qs, request, ListingMinimalSerializer)


@api_view(['GET'])
def list_listings_by_category(request, category_slug):
    """
    Browse listings in a specific category (by slug).
    Query params: same as list_all_listings + optional distance.
    """
    try:
        category = Category.objects.get(slug=category_slug, is_active=True)
    except Category.DoesNotExist:
        return Response({"error": "Category not found."}, status=404)

    qs = Listing.objects.filter(
        category=category, status='active'
    ).select_related('category', 'owner')

    # --- Distance filtering (same as above) ---
    try:
        lat = float(request.GET.get('lat', ''))
        lng = float(request.GET.get('lng', ''))
        radius = float(request.GET.get('radius', ''))
    except (TypeError, ValueError):
        lat = lng = radius = None

    if lat is not None and lng is not None and radius is not None and radius > 0:
        qs = qs.filter(latitude__isnull=False, longitude__isnull=False)
        qs = _annotate_distance(qs, lat, lng)
        qs = qs.filter(distance_km__lte=radius).order_by('distance_km')
    else:
        qs = _apply_listing_filters(qs, request.GET)

    return _paginate(qs, request, ListingMinimalSerializer)


@api_view(['GET'])
def get_listing_detail(request, pk):
    """Full listing detail. Atomically increments view count."""
    try:
        listing = Listing.objects.select_related(
            'category', 'owner', 'owner__profile',
            'room_detail', 'hotel_detail', 'salon_detail',
            'bus_detail', 'restaurant_detail',
        ).prefetch_related('reviews').get(pk=pk, status='active')
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found."}, status=404)

    # Atomic increment — no race condition
    Listing.objects.filter(pk=pk).update(view_count=F('view_count') + 1)

    return Response(ListingSerializer(listing, context={'request': request}).data)


@api_view(['GET'])
def list_featured_listings(request):
    """Featured listings across all categories."""
    qs = Listing.objects.filter(
        status='active', is_featured=True
    ).select_related('category', 'owner').order_by('-created_at')
    return _paginate(qs, request, ListingMinimalSerializer)


# ─── Listings — vendor (owner) actions ───────────────────────────────────────

@api_view(['POST'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def create_listing(request):
    """Create a new listing with optional category-specific detail block."""
    serializer = ListingCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        listing = serializer.save(owner=request.user)
        return Response(
            ListingSerializer(listing, context={'request': request}).data,
            status=201,
        )
    return Response(serializer.errors, status=400)


@api_view(['PATCH'])
@parser_classes([JSONParser, MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def update_listing(request, pk):
    """Partially update your own listing."""
    try:
        listing = Listing.objects.get(pk=pk)
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found."}, status=404)

    if listing.owner_id != request.user.id:
        return Response({"error": "You can only edit your own listings."}, status=403)

    serializer = ListingCreateSerializer(
        listing, data=request.data, partial=True, context={'request': request}
    )
    if serializer.is_valid():
        listing = serializer.save()
        return Response(ListingSerializer(listing, context={'request': request}).data)
    return Response(serializer.errors, status=400)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_listing(request, pk):
    """Delete your own listing."""
    try:
        listing = Listing.objects.get(pk=pk)
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found."}, status=404)

    if listing.owner_id != request.user.id:
        return Response({"error": "You can only delete your own listings."}, status=403)

    listing.delete()
    return Response({"message": "Listing deleted successfully."})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_listings(request):
    """All listings posted by the current user."""
    qs = Listing.objects.filter(owner=request.user).select_related('category')
    status_param = request.GET.get('status')
    if status_param in ('active', 'inactive', 'pending'):
        qs = qs.filter(status=status_param)
    return _paginate(qs, request, ListingMinimalSerializer)


# ─── Saved listings ───────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_save_listing(request):
    """
    Toggle save/unsave on a listing.
    Body: { "listing_id": 123 }
    Returns: { "saved": true } or { "saved": false }
    """
    listing_id = request.data.get('listing_id')
    if not listing_id:
        return Response({"error": "listing_id is required."}, status=400)

    try:
        listing = Listing.objects.get(id=listing_id, status='active')
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found."}, status=404)

    obj, created = SavedListing.objects.get_or_create(user=request.user, listing=listing)
    if not created:
        obj.delete()
        return Response({"saved": False, "message": "Listing removed from saved."})

    return Response({"saved": True, "message": "Listing saved."}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_saved_listings(request):
    """All listings saved by the current user."""
    qs = SavedListing.objects.filter(
        user=request.user
    ).select_related('listing', 'listing__category').order_by('-saved_at')
    return _paginate(qs, request, SavedListingSerializer)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def save_status(request, listing_id):
    """Check whether the current user has saved a specific listing."""
    saved = SavedListing.objects.filter(
        user=request.user, listing_id=listing_id
    ).exists()
    return Response({"saved": saved})


# ─── Image upload ─────────────────────────────────────────────────────────────

ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}
MAX_IMAGE_SIZE_MB = 5


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
@permission_classes([IsAuthenticated])
def upload_images(request):
    """
    Upload one or more images.
    Returns a list of image URLs to attach to a listing's `images` field.
    Field name: 'images' (multiple) or 'image' (single)
    """
    files = request.FILES.getlist('images') or request.FILES.getlist('image')
    if not files:
        return Response(
            {"error": "No images provided. Use field name 'images'."},
            status=400,
        )

    urls = []
    errors = []

    for f in files:
        # Validate type
        if f.content_type not in ALLOWED_IMAGE_TYPES:
            errors.append(f"{f.name}: unsupported file type ({f.content_type}). "
                          f"Allowed: jpeg, png, webp, gif.")
            continue

        # Validate size
        if f.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
            errors.append(f"{f.name}: file too large (max {MAX_IMAGE_SIZE_MB}MB).")
            continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")
        # Sanitise filename
        safe_name = "".join(c if c.isalnum() or c in ('_', '.', '-') else '_' for c in f.name)
        filename = f"listing_images/{timestamp}_{safe_name}"
        saved_path = default_storage.save(filename, f)
        url = request.build_absolute_uri(f"{settings.MEDIA_URL}{saved_path}")

        UploadedImage.objects.create(
            uploaded_by=request.user,
            image=saved_path,
            url=url,
        )
        urls.append(url)

    response = {"image_urls": urls}
    if errors:
        response["errors"] = errors

    status_code = 201 if urls else 400
    return Response(response, status=status_code)
