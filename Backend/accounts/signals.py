# This file contains signal handlers for the accounts app.
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Role


@receiver(post_save, sender=User)
def create_profile_for_new_user(sender, instance, created, **kwargs):
    if created:
        # default role for now; we will set correctly during signup later
        Profile.objects.create(
            user=instance,
            role=Role.PATIENT,
            full_name=instance.get_full_name() or instance.username,
        )