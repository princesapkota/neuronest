from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Role


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
@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(
            user=instance,
            defaults={
                "role": Role.PATIENT,  # keep patient if you want default
                "full_name": instance.get_full_name() or instance.username,
            }
        )