from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Role


# this runs automatically every time a new User is made, so a matching Profile always gets created with them
@receiver(post_save, sender=User)
def ensure_profile_exists(sender, instance, created, **kwargs):
    """
    Create a Profile only if it's missing.
    Never overwrite role for existing profiles.
    """
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "role": Role.PATIENT,  # fallback default
                "full_name": instance.get_full_name() or instance.username,
            }
        )