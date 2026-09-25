import random
import uuid
from decimal import Decimal
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User

from movies.models import Movie, Theater, Seat, Booking, PaymentTransaction


class Command(BaseCommand):
    help = "Seed high-volume realistic benchmark bookings and transactions (supports 100,000+ records) with zero memory overhead."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=100000,
            help='Number of benchmark bookings to seed (default: 100,000)'
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Remove all benchmark-seeded bookings and transactions'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=5000,
            help='Batch size for bulk_create operations (default: 5,000)'
        )

    def handle(self, *args, **options):
        clean_only = options['clean']
        total_count = options['count']
        batch_size = options['batch_size']

        if clean_only:
            self.stdout.write(self.style.WARNING("Purging benchmark bookings, transactions, seats, and theaters..."))
            deleted_b, _ = Booking.objects.filter(booking_id__startswith="PMS-BENCH-").delete()
            deleted_tx, _ = PaymentTransaction.objects.filter(booking_id__startswith="PMS-BENCH-").delete()
            deleted_t, _ = Theater.objects.filter(name__startswith="[Benchmark]").delete()
            self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_b} bookings, {deleted_tx} transactions, and {deleted_t} theaters."))
            return

        self.stdout.write(self.style.NOTICE(f"Initiating high-performance seeding of {total_count:,} benchmark records..."))

        movies = list(Movie.objects.all())
        if not movies:
            self.stdout.write(self.style.ERROR("No movies found in database. Please seed movies first."))
            return

        users = list(User.objects.all())
        if not users:
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            users = [admin_user]

        # 1. Create dedicated benchmark theaters and screens if needed
        # We need enough seats to accommodate total_count bookings (1 seat per booking)
        existing_bench_theaters = list(Theater.objects.filter(name__startswith="[Benchmark]"))
        seats_per_theater = 100
        theaters_needed = max(1, (total_count + seats_per_theater - 1) // seats_per_theater)

        if len(existing_bench_theaters) < theaters_needed:
            theaters_to_create_count = theaters_needed - len(existing_bench_theaters)
            self.stdout.write(f"Creating {theaters_to_create_count} benchmark theaters to support {total_count:,} seats...")

            cities = ['Mumbai', 'Delhi-NCR', 'Bengaluru', 'Hyderabad', 'Chennai', 'Pune']
            chains = ['PVR Inox', 'Cinepolis', 'Miraj Cinemas', 'PVR IMAX', 'Carnival']
            new_theaters = []
            now = timezone.now()

            for i in range(len(existing_bench_theaters), theaters_needed):
                movie = movies[i % len(movies)]
                city = cities[i % len(cities)]
                chain = chains[i % len(chains)]
                show_time = now - timedelta(days=(i % 180), hours=(i % 12))
                new_theaters.append(
                    Theater(
                        name=f"[Benchmark] {chain} Audi {((i % 5) + 1)}",
                        movie=movie,
                        city=city,
                        theater_chain=chain,
                        screen_name=f"Screen {((i % 5) + 1)}",
                        price=Decimal(random.choice(['180.00', '220.00', '250.00', '320.00', '450.00'])),
                        time=show_time
                    )
                )

            with transaction.atomic():
                Theater.objects.bulk_create(new_theaters, batch_size=2000)

            all_bench_theaters = list(Theater.objects.filter(name__startswith="[Benchmark]"))
        else:
            all_bench_theaters = existing_bench_theaters[:theaters_needed]

        self.stdout.write(f"Verified {len(all_bench_theaters)} benchmark theaters.")

        # 2. Check existing benchmark seats or bulk create seats
        total_existing_seats = Seat.objects.filter(theater__in=all_bench_theaters).count()
        seats_needed = total_count - total_existing_seats

        if seats_needed > 0:
            self.stdout.write(f"Generating {seats_needed:,} auditorium seats...")
            new_seats = []
            for t_idx, theater in enumerate(all_bench_theaters):
                cur_seat_count = theater.seats.count()
                seats_for_this = min(seats_per_theater - cur_seat_count, total_count)
                if seats_for_this <= 0:
                    continue

                for s in range(seats_for_this):
                    row_char = chr(65 + (s // 10))
                    seat_num = f"{row_char}{((s % 10) + 1)}"
                    new_seats.append(
                        Seat(
                            theater=theater,
                            seat_number=seat_num,
                            is_booked=True
                        )
                    )
                    if len(new_seats) >= seats_needed:
                        break
                if len(new_seats) >= seats_needed:
                    break

            with transaction.atomic():
                Seat.objects.bulk_create(new_seats, batch_size=5000)
            self.stdout.write(f"Successfully generated {len(new_seats):,} seats.")

        # 3. Retrieve available seats in benchmark theaters that don't have bookings yet
        self.stdout.write("Fetching unassigned benchmark seats for booking generation...")
        unbooked_seat_ids = list(
            Seat.objects.filter(theater__in=all_bench_theaters, booking__isnull=True)
            .values_list('id', 'theater_id', 'theater__movie_id', 'theater__price')[:total_count]
        )

        seats_to_book_count = len(unbooked_seat_ids)
        self.stdout.write(f"Found {seats_to_book_count:,} available seats to assign bookings.")

        if seats_to_book_count == 0:
            self.stdout.write(self.style.SUCCESS("All benchmark seats are already booked!"))
            return

        # 4. Generate Bookings and PaymentTransactions in memory and bulk_create in chunks
        self.stdout.write(f"Generating {seats_to_book_count:,} bookings in batches of {batch_size}...")

        base_time = timezone.now()
        user_ids = [u.id for u in users]

        # Weights for realistic distribution:
        # Peak booking hours: 18:00 to 22:00 (Evening rush), 12:00 to 14:00 (Lunchtime), other hours
        hours_distribution = [18, 19, 20, 21, 22, 12, 13, 14, 15, 16, 17, 10, 11, 23, 9, 8, 7, 0, 1, 2, 3, 4, 5, 6]
        hour_weights = [15, 18, 20, 14, 10, 8, 7, 5, 4, 4, 6, 4, 3, 2, 2, 1, 1, 1, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]

        # Status distribution: 88% CONFIRMED, 5% PAID, 7% CANCELLED
        statuses = ['CONFIRMED', 'PAID', 'CANCELLED']
        status_weights = [0.88, 0.05, 0.07]

        # PaymentTransaction status distribution: 85% SUCCESS, 7% REFUNDED, 8% FAILED
        txn_statuses = ['SUCCESS', 'REFUNDED', 'FAILED']
        txn_status_weights = [0.85, 0.07, 0.08]

        created_bookings_count = 0
        created_txns_count = 0

        # We will loop in batches
        for chunk_start in range(0, seats_to_book_count, batch_size):
            chunk = unbooked_seat_ids[chunk_start:chunk_start + batch_size]
            booking_objs = []
            txn_objs = []

            for seat_id, theater_id, movie_id, price in chunk:
                # Distribute booked_at across the past 365 days
                days_ago = random.randint(0, 364)
                hour = random.choices(hours_distribution, weights=hour_weights, k=1)[0]
                minute = random.randint(0, 59)
                second = random.randint(0, 59)

                booked_timestamp = base_time - timedelta(days=days_ago)
                booked_timestamp = booked_timestamp.replace(hour=hour, minute=minute, second=second)

                user_id = random.choice(user_ids)
                status = random.choices(statuses, weights=status_weights, k=1)[0]
                b_uid = f"{uuid.uuid4().hex[:12].upper()}_{seat_id}"
                booking_id = f"PMS-BENCH-{b_uid}"
                pay_ref = f"PAY-BENCH-{uuid.uuid4().hex[:12].upper()}"

                booking_objs.append(
                    Booking(
                        user_id=user_id,
                        seat_id=seat_id,
                        movie_id=movie_id,
                        theater_id=theater_id,
                        booking_id=booking_id,
                        payment_reference=pay_ref,
                        total_price=price,
                        payment_status=status,
                        email_sent=True,
                        booked_at=booked_timestamp
                    )
                )

                # Generate a payment transaction for ~60% of bookings
                if random.random() < 0.60:
                    txn_status = random.choices(txn_statuses, weights=txn_status_weights, k=1)[0]
                    txn_objs.append(
                        PaymentTransaction(
                            user_id=user_id,
                            booking_id=booking_id,
                            movie_id=movie_id,
                            theater_id=theater_id,
                            gateway='RAZORPAY',
                            order_id=f"order_bench_{uuid.uuid4().hex}",
                            payment_id=f"pay_bench_{uuid.uuid4().hex}" if txn_status != 'FAILED' else None,
                            amount=price,
                            currency='INR',
                            status=txn_status,
                            seat_numbers=f"B-{seat_id}",
                            seat_ids=str(seat_id),
                            payment_method='UPI/Credit Card',
                            created_at=booked_timestamp,
                            updated_at=booked_timestamp
                        )
                    )

            with transaction.atomic():
                Booking.objects.bulk_create(booking_objs, batch_size=2500)
                if txn_objs:
                    PaymentTransaction.objects.bulk_create(txn_objs, batch_size=2500)

            created_bookings_count += len(booking_objs)
            created_txns_count += len(txn_objs)
            progress_pct = (created_bookings_count / seats_to_book_count) * 100
            self.stdout.write(f"  -> Seeded {created_bookings_count:,} / {seats_to_book_count:,} bookings ({progress_pct:.1f}%)...")

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded {created_bookings_count:,} benchmark bookings and {created_txns_count:,} payment transactions!"
        ))
