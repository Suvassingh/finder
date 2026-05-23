from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Review


class ReviewerSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'profile_image']

    def get_profile_image(self, obj):
        request = self.context.get('request')
        try:
            if obj.profile and obj.profile.profile_image:
                if request:
                    return request.build_absolute_uri(obj.profile.profile_image.url)
                return obj.profile.profile_image.url
        except Exception:
            pass
        return None


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = ReviewerSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'reviewer', 'rating', 'title', 'body', 'created_at', 'updated_at']


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['rating', 'title', 'body']

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
