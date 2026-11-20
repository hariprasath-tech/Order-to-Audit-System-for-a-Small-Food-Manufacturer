"""
Management command to create benchmark demo users across the 5 factory role groups.
Idempotent and safe to rerun multiple times.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

DEMO_PASSWORD = "Demo@1234"

DEMO_USERS = [
    ("salesman_a", "salesman", "Salesman A (North Route)"),
    ("salesman_b", "salesman", "Salesman B (South Route)"),
    ("admin_user", "admin_desk", "Factory Admin Desk"),
    ("production", "production", "Production Supervisor"),
    ("accountant", "accountant", "Factory Auditor & Accountant"),
    ("owner", "owner", "Factory Owner / Managing Director"),
]


class Command(BaseCommand):
    help = "Creates or updates the 6 standard benchmark demo users for all role groups."

    def handle(self, *args, **options):
        User = get_user_model()
        created_count = 0
        updated_count = 0

        for username, group_name, display_label in DEMO_USERS:
            group, _ = Group.objects.get_or_create(name=group_name)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"first_name": display_label},
            )
            user.set_password(DEMO_PASSWORD)
            user.save()
            user.groups.add(group)

            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created demo user: {username} [{group_name}] ({display_label})"
                    )
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.NOTICE(
                        f"Updated demo user: {username} [{group_name}] (password reset)"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully initialized demo users ({created_count} created, {updated_count} updated)."
            )
        )
