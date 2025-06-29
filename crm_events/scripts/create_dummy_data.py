import os
import django
from django.db import transaction
from faker import Faker
import random
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'config.settings')
django.setup()

from crm_events.models import CustomUser, Event, EventParticipation

fake = Faker()


def create_dummy_users(num_users=50):
    print(f"Creating {num_users} dummy users...")
    users = []
    CustomUser.objects.all().delete()

    for _ in range(num_users):
        first_name = fake.first_name()
        last_name = fake.last_name()
        username = fake.user_name()[:100] + str(random.randint(1, 10000))
        email = f"{username}@example.com"

        # Loop until unique username/email is found
        attempts = 0
        while (CustomUser.objects.filter(username=username).exists() or
               CustomUser.objects.filter(email=email).exists()) and attempts < 100:
            username = fake.user_name()[:100] + str(random.randint(1, 10000))
            email = f"{username}@example.com"
            attempts += 1

        if attempts >= 100:
            print(f"Warning: Could not create unique username/email after 100 attempts for a user.")
            continue

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password='password123',
            first_name=first_name,
            last_name=last_name,
            phone_number=fake.phone_number() if hasattr(CustomUser, 'phone_number') else '',
            gender=random.choice(['M', 'F', 'O']) if hasattr(CustomUser, 'gender') else 'O',
            job_title=fake.job() if hasattr(CustomUser, 'job_title') else '',
            company=fake.company() if hasattr(CustomUser, 'company') else '',
            city=fake.city() if hasattr(CustomUser, 'city') else '',
            state=fake.state_abbr() if hasattr(CustomUser, 'state') else '',
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

    Event.objects.all().delete()

    for i in range(num_events):
        owner = random.choice(users)

        base_title = fake.catch_phrase()
        title = f"{base_title} Event {i + 1}"
        slug_candidate = fake.slug(value=base_title) + f"-{i + 1}-{random.randint(100, 9999)}"

        attempts = 0
        while Event.objects.filter(slug=slug_candidate).exists() and attempts < 100:
            slug_candidate = fake.slug(value=base_title) + f"-{i + 1}-{random.randint(100, 9999)}"
            attempts += 1

        if attempts >= 100:
            print(f"Warning: Could not create unique slug for event '{title}' after 100 attempts.")
            continue  # Skip this event creation

        description = fake.paragraph(nb_sentences=5)

        start_at = fake.date_time_between(start_date='-1y', end_date='+1y',
                                          tzinfo=timezone.get_current_timezone())
        end_at = start_at + timedelta(hours=random.randint(1, 8))

        venue = fake.address()
        max_capacity = random.choice([50, 100, 200, 500, None])

        event = Event.objects.create(
            slug=slug_candidate,
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
            # Randomly select unique hosts
            selected_hosts = random.sample(potential_hosts, k=min(num_hosts, len(potential_hosts)))

            for host_user in selected_hosts:
                try:
                    EventParticipation.objects.create(event=event, user=host_user,
                                                      role=EventParticipation.ROLE_HOST)
                except Exception as e:
                    print(f"Could not add host {host_user.username} to event {event.title}: {e}")

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
        current_participants = set(p.user for p in EventParticipation.objects.filter(event=event))

        potential_attendees = list(set(users) - current_participants - {event.owner})

        num_to_add = random.randint(0, min(num_attendees_per_event, len(potential_attendees)))

        current_total_participants_count = EventParticipation.objects.filter(event=event).count()
        if event.max_capacity is not None:
            available_slots = event.max_capacity - current_total_participants_count
            num_to_add = min(num_to_add, available_slots)

        if num_to_add > 0:
            selected_attendees = random.sample(potential_attendees, k=num_to_add)

            for attendee_user in selected_attendees:
                try:
                    EventParticipation.objects.create(event=event, user=attendee_user,
                                                      role=EventParticipation.ROLE_ATTENDEE)
                    total_added_attendees += 1
                except Exception as e:
                    print(
                        f"Could not add attendee {attendee_user.username} to event {event.title}: {e}")

    print(f"Added {total_added_attendees} attendees across events.")


@transaction.atomic
def run():
    print("--- Starting dummy data generation ---")
    print("Cleaning up existing data...")
    CustomUser.objects.all().delete()

    users = create_dummy_users(num_users=50)
    events = create_dummy_events(users, num_events=30)

    if users and events:
        add_dummy_attendees(users, events, num_attendees_per_event=random.randint(5, 20))

    print("--- Dummy data generation complete ---")


if __name__ == '__main__':
    run()