import os
import django
from django.db import transaction
from faker import Faker
import random
from datetime import timedelta
from django.utils import timezone  # Import timezone for better datetime handling

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'config.settings')  # Ensure this points to your actual settings file
django.setup()

# Import your models
from crm_events.models import CustomUser, Event  # REMOVED EventRegistration import

fake = Faker()


def create_dummy_users(num_users=50):
    print(f"Creating {num_users} dummy users...")
    users = []
    for _ in range(num_users):
        first_name = fake.first_name()
        last_name = fake.last_name()
        username = fake.user_name()[:10] + str(random.randint(1, 10000))
        email = f"{username}@example.com"
        password = 'password123'

        while CustomUser.objects.filter(username=username).exists() or \
                CustomUser.objects.filter(email=email).exists():  # Also check email existence
            username = fake.user_name()[:10] + str(random.randint(1, 10000))
            email = f"{username}@example.com"

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            # Ensure these fields exist on your CustomUser model, or remove them
            # if you are just using the default Django User model without extensions
            phone_number=fake.phone_number() if hasattr(CustomUser, 'phone_number') else None,
            gender=random.choice(['M', 'F', 'O']) if hasattr(CustomUser, 'gender') else None,
            job_title=fake.job() if hasattr(CustomUser, 'job_title') else None,
            company=fake.company() if hasattr(CustomUser, 'company') else None,
            city=fake.city() if hasattr(CustomUser, 'city') else None,
            state=fake.state_abbr() if hasattr(CustomUser, 'state') else None,
        )
        users.append(user)
    print(f"Created {len(users)} users.")
    return users


def create_dummy_events(users, num_events=30):
    print(f"Creating {num_events} dummy events...")
    events = []
    if not users:
        print("No users available to assign as owners/hosts for events.")
        return []

    for i in range(num_events):
        owner = random.choice(users)

        # Make sure your slug generation is robust to avoid duplicates
        base_title = fake.catch_phrase()
        title = f"{base_title} Event {i + 1}"
        slug_candidate = fake.slug(value=base_title) + f"-{i + 1}-{random.randint(100, 9999)}"

        # Ensure slug is unique
        while Event.objects.filter(slug=slug_candidate).exists():
            slug_candidate = fake.slug(value=base_title) + f"-{i + 1}-{random.randint(100, 9999)}"

        description = fake.paragraph(nb_sentences=5)

        # Use timezone.now() for timezone-aware datetimes
        start_at = fake.date_time_between(start_date='-1y', end_date='+1y',
                                          tzinfo=timezone.get_current_timezone())
        end_at = start_at + timedelta(hours=random.randint(1, 8))

        venue = fake.address()
        max_capacity = random.choice([50, 100, 200, 500, None])

        event = Event.objects.create(
            slug=slug_candidate,  # Use the generated unique slug
            title=title,
            description=description,
            start_at=start_at,
            end_at=end_at,
            venue=venue,
            max_capacity=max_capacity,
            owner=owner
        )

        # Assign random hosts (excluding the owner, if possible)
        num_hosts = random.randint(0, min(3, len(users) - 1))
        potential_hosts = [u for u in users if u != owner]
        if potential_hosts:
            hosts = random.sample(potential_hosts, k=min(num_hosts, len(potential_hosts)))
            event.hosts.set(hosts)  # Use .set() for ManyToMany

        events.append(event)
    print(f"Created {len(events)} events.")
    return events


def add_dummy_attendees(users, events, num_attendees_per_event=10):
    print(f"Adding dummy attendees to events...")
    if not users or not events:
        print("Cannot add attendees: No users or events available.")
        return

    total_added_attendees = 0
    for event in events:
        # Exclude existing hosts and owner from potential attendees for this event
        # and ensure we don't pick the same user twice if max_capacity is large
        potential_attendees = list(set(users) - set(event.hosts.all()) - {event.owner})

        # Determine how many attendees to add, respecting max_capacity
        num_to_add = random.randint(0, min(num_attendees_per_event, len(potential_attendees)))
        if event.max_capacity is not None:
            current_attendees_count = event.attendees.count()
            available_slots = event.max_capacity - current_attendees_count
            num_to_add = min(num_to_add, available_slots)

        if num_to_add > 0:
            selected_attendees = random.sample(potential_attendees, k=num_to_add)
            event.attendees.add(*selected_attendees)  # Add attendees
            total_added_attendees += num_to_add

    print(f"Added {total_added_attendees} attendees across events.")


def run():
    print("--- Starting dummy data generation ---")
    with transaction.atomic():
        # Clean up existing data to avoid duplicates/conflicts during testing
        print("Cleaning up existing CustomUser, Event data...")
        # Note: Deleting CustomUser might delete related Events due to CASCADE
        # Consider order if you want to preserve some data. For a clean slate:
        CustomUser.objects.all().delete()
        # Event.objects.all().delete() # Events will be deleted with CustomUser if CustomUser is owner

        users = create_dummy_users(num_users=50)
        events = create_dummy_events(users, num_events=30)
        add_dummy_attendees(users, events,
                            num_attendees_per_event=random.randint(5, 20))  # Add attendees

        print("--- Dummy data generation complete ---")


if __name__ == '__main__':
    run()
