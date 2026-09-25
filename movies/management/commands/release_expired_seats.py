from django.core.management.base import BaseCommand
from django.utils import timezone
from movies.models import Seat, Theater, PaymentTransaction
from movies.views import clean_expired_reservations


class Command(BaseCommand):
    help = 'Releases expired 2-minute temporary seat reservations and stale checkout holds across all theaters.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--theater-id',
            type=int,
            help='Filter cleanup to a specific Theater ID (optional)',
            default=None
        )
        parser.add_argument(
            '--max-age-minutes',
            type=int,
            help='Maximum age in minutes for stale checkout holds (default: 2)',
            default=2
        )

    def handle(self, *args, **options):
        theater_id = options.get('theater_id')
        max_age = options.get('max_age_minutes') or 2
        now = timezone.now()

        theater = None
        if theater_id:
            try:
                theater = Theater.objects.get(id=theater_id)
                self.stdout.write(f"Scoping cleanup to theater: {theater.name} (ID: {theater.id})")
            except Theater.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Theater with ID {theater_id} does not exist."))
                return

        # Pre-count expired seats
        expired_query = Seat.objects.filter(is_booked=False, reserved_until__lte=now)
        if theater:
            expired_query = expired_query.filter(theater=theater)
        expired_count = expired_query.count()

        # Run cleanup
        clean_expired_reservations(theater=theater)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully released {expired_count} expired seat reservation(s) "
                f"and cleared stale holds older than {max_age} minute(s)."
            )
        )
