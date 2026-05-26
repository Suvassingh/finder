from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Listing
from notifications.utils import send_push_notification
from django.contrib.auth.models import User

@receiver(post_save, sender=Listing)
def notify_on_new_listing(sender, instance, created, **kwargs):
    if created:
        # Notify all staff users (admins & moderators)
        staff_users = User.objects.filter(is_staff=True)
        for admin_user in staff_users:
            send_push_notification(
                admin_user,
                "New listing created",
                f"{instance.owner.first_name} posted: {instance.title}",
                data={'listing_id': instance.id}
            )
        followers = instance.category.followers.select_related('user')
        for follow in followers:
            # Don't notify the owner themselves
            if follow.user != instance.owner:
                send_push_notification(
                    follow.user,
                    f"New {instance.category.name} listing",
                    f"{instance.owner.first_name} posted: {instance.title}",
                    data={'listing_id': instance.id}
                )
@receiver(post_save, sender=Listing)
def notify_category_followers_on_new_listing(sender, instance, created, **kwargs):
    if not created:
        return  # Only notify for new listings

    category = instance.category
    followers = category.followers.select_related('user')
    
    for follow in followers:
        user = follow.user
        # Don't notify the listing owner (optional)
        if user == instance.owner:
            continue
        
        send_push_notification(
            user,
            f"New {category.name} listing",
            f"{instance.owner.first_name} posted: {instance.title}",
            data={'listing_id': instance.id}
        )