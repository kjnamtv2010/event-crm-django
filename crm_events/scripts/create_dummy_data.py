import os
import django
from django.db import transaction
from faker import Faker
import random
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'event-crm-django.settings')
django.setup()

from crm_events.models import CustomUser, Event, EventRegistration

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

        while CustomUser.objects.filter(username=username).exists():
            username = fake.user_name()[:10] + str(random.randint(1, 10000))
            email = f"{username}@example.com"

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=fake.phone_number(),
            gender=random.choice(['M', 'F', 'O']),
            job_title=fake.job(),
            company=fake.company(),
            city=fake.city(),
            state=fake.state_abbr(),
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
        title = fake.catch_phrase() + f" Event {i + 1}"
        slug = fake.slug() + f"-event-{i + 1}-{random.randint(100, 999)}"
        description = fake.paragraph(nb_sentences=5)
        start_at = fake.date_time_between(start_date='-1y', end_date='+1y', tzinfo=None)
        end_at = start_at + timedelta(hours=random.randint(1, 8))
        venue = fake.address()
        max_capacity = random.choice([50, 100, 200, 500, None])

        while Event.objects.filter(slug=slug).exists():
            slug = fake.slug() + f"-event-{i + 1}-{random.randint(100, 999)}"

        event = Event.objects.create(
            slug=slug,
            title=title,
            description=description,
            start_at=start_at,
            end_at=end_at,
            venue=venue,
            max_capacity=max_capacity,
            owner=owner
        )

        num_hosts = random.randint(0, min(3, len(users) - 1))
        potential_hosts = [u for u in users if u != owner]
        if potential_hosts:
            hosts = random.sample(potential_hosts, k=min(num_hosts, len(potential_hosts)))
            event.hosts.set(hosts)

        events.append(event)
    print(f"Created {len(events)} events.")
    return events


def create_dummy_registrations(users, events, num_registrations=100):
    print(f"Creating {num_registrations} dummy event registrations...")
    if not users or not events:
        print("Cannot create registrations: No users or events available.")
        return

    existing_registrations = set(
        EventRegistration.objects.values_list('user', 'event')
    )

    created_count = 0
    attempts = 0
    max_attempts_per_registration = 50

    while created_count < num_registrations and attempts < num_registrations * max_attempts_per_registration:
        user = random.choice(users)
        event = random.choice(events)

        attempts += 1

        current_registrations_count = EventRegistration.objects.filter(event=event).count()
        if event.max_capacity is not None and current_registrations_count >= event.max_capacity:
            continue

        if (user.id, event.id) in existing_registrations:
            continue

        try:
            EventRegistration.objects.create(
                user=user,
                event=event,
                registered_at=fake.date_time_this_year(before_now=True, after_now=False,
                                                       tzinfo=None)
            )
            existing_registrations.add((user.id, event.id))
            created_count += 1
        except Exception as e:
            print(f"Error creating registration: {e}. Retrying...")
            continue

    print(f"Created {created_count} event registrations.")


def run():
    print("--- Starting dummy data generation ---")
    with transaction.atomic():
        users = create_dummy_users(num_users=50)
        events = create_dummy_events(users, num_events=30)
        create_dummy_registrations(users, events, num_registrations=100)
        print("--- Dummy data generation complete ---")
