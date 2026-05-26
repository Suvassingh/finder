from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts import serializers
from listings.models import Listing
from notifications.utils import send_push_notification
from .models import Review
from .serializers import ReviewCreateSerializer, ReviewSerializer


@api_view(['GET'])
def list_reviews(request, listing_id):
    """Public: get all reviews for a listing, newest first."""
    reviews = Review.objects.filter(
        listing_id=listing_id
    ).select_related('reviewer', 'reviewer__profile')
    return Response(ReviewSerializer(reviews, many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_review(request, listing_id):
    """Authenticated: post a review for a listing."""
    try:
        listing = Listing.objects.get(pk=listing_id, status='active')
    except Listing.DoesNotExist:
        return Response({"error": "Listing not found."}, status=404)
    review = serializers.save(listing=listing, reviewer=request.user)
    if listing.owner != request.user:
        send_push_notification(
            listing.owner,
            "New review on your listing",
            f"{request.user.first_name} rated '{listing.title}' {review.rating}★",
            data={'listing_id': listing.id}
        )
    return Response(ReviewSerializer(review, context={'request': request}).data, status=201)

    if listing.owner_id == request.user.id:
        return Response({"error": "You cannot review your own listing."}, status=400)

    if Review.objects.filter(listing=listing, reviewer=request.user).exists():
        return Response({"error": "You have already reviewed this listing."}, status=400)

    serializer = ReviewCreateSerializer(data=request.data)
    if serializer.is_valid():
        review = serializer.save(listing=listing, reviewer=request.user)
        return Response(
            ReviewSerializer(review, context={'request': request}).data,
            status=201,
        )
    return Response(serializer.errors, status=400)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def manage_review(request, review_id):
    """Edit or delete your own review."""
    try:
        review = Review.objects.get(pk=review_id, reviewer=request.user)
    except Review.DoesNotExist:
        return Response({"error": "Review not found or not yours."}, status=404)

    if request.method == 'DELETE':
        review.delete()
        return Response({"message": "Review deleted."})

    # PATCH
    serializer = ReviewCreateSerializer(review, data=request.data, partial=True)
    if serializer.is_valid():
        review = serializer.save()
        return Response(ReviewSerializer(review, context={'request': request}).data)
    return Response(serializer.errors, status=400)
