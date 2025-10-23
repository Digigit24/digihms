# apps/doctors/management/commands/seed_doctors.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from decimal import Decimal
from datetime import time

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with sample Doctors, Specialties, and Availability (idempotent)"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting doctors seeding…")

        # Import here to avoid app registry issues
        from apps.doctors.models import Specialty, DoctorProfile, DoctorAvailability

        # 1) Ensure Doctor group
        doctor_group, _ = Group.objects.get_or_create(name="Doctor")

        # 2) Ensure specialties
        self.stdout.write("Ensuring specialties…")
        spec_defs = [
            {"code": "CARD", "name": "Cardiology", "is_active": True},
            {"code": "GEN",  "name": "General Medicine", "is_active": True},
            {"code": "ORTH", "name": "Orthopedics", "is_active": True},
        ]
        code_to_spec = {}
        for sd in spec_defs:
            spec, _ = Specialty.objects.get_or_create(
                code=sd["code"],
                defaults={
                    "name": sd["name"],
                    "is_active": sd["is_active"],
                },
            )
            # If name changed later, keep data consistent without breaking idempotency
            if spec.name != sd["name"]:
                spec.name = sd["name"]
                spec.save(update_fields=["name"])
            code_to_spec[sd["code"]] = spec

        # 3) Ensure users (doctors) and link to group
        self.stdout.write("Ensuring doctor users…")
        doctor_users = [
            {
                "username": "dr.sharma",
                "email": "dr.sharma@hospital.com",
                "first_name": "Rajesh",
                "last_name": "Sharma",
                "password": "doctor123",
                "specialties": ["CARD"],
                "profile_defaults": {
                    "medical_license_number": "MH/DOC/12345",
                    "consultation_fee": Decimal("800.00"),
                    "follow_up_fee": Decimal("400.00"),
                    "status": "active",
                    "years_of_experience": 10,
                    "consultation_duration": 15,
                    "is_available_online": False,
                    "is_available_offline": True,
                },
            },
            {
                "username": "dr.patel",
                "email": "dr.patel@hospital.com",
                "first_name": "Priya",
                "last_name": "Patel",
                "password": "doctor123",
                "specialties": ["GEN"],
                "profile_defaults": {
                    "medical_license_number": "MH/DOC/67890",
                    "consultation_fee": Decimal("600.00"),
                    "follow_up_fee": Decimal("300.00"),
                    "status": "active",
                    "years_of_experience": 7,
                    "consultation_duration": 15,
                    "is_available_online": False,
                    "is_available_offline": True,
                },
            },
            {
                "username": "dr.kale",
                "email": "dr.kale@hospital.com",
                "first_name": "Amit",
                "last_name": "Kale",
                "password": "doctor123",
                "specialties": ["ORTH"],
                "profile_defaults": {
                    "medical_license_number": "MH/DOC/24680",
                    "consultation_fee": Decimal("700.00"),
                    "follow_up_fee": Decimal("350.00"),
                    "status": "active",
                    "years_of_experience": 9,
                    "consultation_duration": 15,
                    "is_available_online": False,
                    "is_available_offline": True,
                },
            },
        ]

        username_to_profile = {}

        for du in doctor_users:
            user, created = User.objects.get_or_create(
                username=du["username"],
                defaults={
                    "email": du["email"],
                    "first_name": du["first_name"],
                    "last_name": du["last_name"],
                    "is_active": True,
                },
            )
            # Set password only when newly created (don’t overwrite existing)
            if created:
                user.set_password(du["password"])
                user.save(update_fields=["password"])
            # Ensure in Doctor group
            user.groups.add(doctor_group)

            # Create/Update DoctorProfile (OneToOne)
            profile, _ = DoctorProfile.objects.update_or_create(
                user=user,
                defaults=du["profile_defaults"],
            )

            # Attach specialties idempotently
            specs = [code_to_spec[c] for c in du["specialties"] if c in code_to_spec]
            if specs:
                profile.specialties.add(*specs)

            username_to_profile[du["username"]] = profile

        # 4) Ensure availability for each doctor (unique_together: doctor, day_of_week, start_time)
        #    This makes the command re-runnable without duplicates.
        self.stdout.write("Ensuring availability slots…")

        def ensure_slot(profile, day, start, end, max_appts=0, is_avail=True):
            DoctorAvailability.objects.get_or_create(
                doctor=profile,
                day_of_week=day,
                start_time=start,
                defaults={
                    "end_time": end,
                    "is_available": is_avail,
                    "max_appointments": max_appts,
                },
            )
            # If a slot exists but end_time / flags changed later, update safely:
            DoctorAvailability.objects.filter(
                doctor=profile,
                day_of_week=day,
                start_time=start,
            ).update(
                end_time=end,
                is_available=is_avail,
                max_appointments=max_appts,
            )

        # A simple schedule: Mon–Fri (10:00–13:00 & 17:00–20:00), Sat (10:00–14:00)
        weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        for username, profile in username_to_profile.items():
            for d in weekdays:
                ensure_slot(profile, d, time(10, 0), time(13, 0), max_appts=12, is_avail=True)
                ensure_slot(profile, d, time(17, 0), time(20, 0), max_appts=12, is_avail=True)
            # Saturday
            ensure_slot(profile, "saturday", time(10, 0), time(14, 0), max_appts=10, is_avail=True)
            # Sunday off (explicitly set/unset if you want):
            # ensure_slot(profile, "sunday", time(0, 0), time(0, 1), max_appts=0, is_avail=False)

        self.stdout.write(self.style.SUCCESS("✓ Doctors seeding complete (idempotent)."))
