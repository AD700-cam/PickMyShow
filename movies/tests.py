from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import datetime
import json

from .models import (
    Movie, Theater, Seat, Booking, RecentlyViewed,
    Genre, Language, CastMember, MoviePoster, Review, ReviewReport,
    PaymentTransaction
)
from .payment_gateway import (
    create_razorpay_order, generate_payment_signature,
    verify_razorpay_signature, verify_razorpay_webhook_signature,
    get_razorpay_webhook_secret, get_razorpay_key_secret
)
from .views import get_personalized_recommendations
from .analytics import DashboardAnalyticsService


class MovieDiscoveryTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='moviefan', password='password123', email='fan@example.com')

        now = timezone.now()
        # Create test movies
        self.movie1 = Movie.objects.create(
            name='Interstellar Odyssey',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('8.9'),
            release_date=datetime.date(2024, 1, 10),
            duration=165,
            cast='Matthew Cooper, Anne Brand',
            description='A deep space mission to save humanity.'
        )
        self.movie2 = Movie.objects.create(
            name='The Cyber Warrior',
            genre='Action',
            language='English',
            rating=Decimal('7.9'),
            release_date=datetime.date(2023, 11, 15),
            duration=130,
            cast='John Wick, Keanu Matrix',
            description='An action packed thriller in a dystopian city.'
        )
        self.movie3 = Movie.objects.create(
            name='Laughter Riot',
            genre='Comedy',
            language='Hindi',
            rating=Decimal('8.2'),
            release_date=datetime.date(2024, 5, 20),
            duration=115,
            cast='Ravi Kumar, Pankaj Sharma',
            description='A hilarious comedy of errors.'
        )
        self.movie4 = Movie.objects.create(
            name='Sci-Fi Chronicles',
            genre='Sci-Fi',
            language='Tamil',
            rating=Decimal('9.1'),
            release_date=datetime.date(2024, 6, 1),
            duration=150,
            cast='Vikram Surya, Kamal Sethu',
            description='Time travel and futuristic adventures.'
        )

        # Create Theaters & Shows in different cities, times & prices
        # Morning show in Mumbai (9:30 AM)
        morning_time = now.replace(hour=9, minute=30, second=0, microsecond=0)
        self.theater1 = Theater.objects.create(
            name='PVR ICON Mumbai',
            movie=self.movie1,
            time=morning_time,
            city='Mumbai',
            theater_chain='PVR',
            price=Decimal('250.00')
        )
        # Evening show in Delhi (6:30 PM)
        evening_time = now.replace(hour=18, minute=30, second=0, microsecond=0)
        self.theater2 = Theater.objects.create(
            name='INOX Delhi',
            movie=self.movie2,
            time=evening_time,
            city='Delhi-NCR',
            theater_chain='INOX',
            price=Decimal('350.00')
        )
        # Night show in Bengaluru (9:30 PM)
        night_time = now.replace(hour=21, minute=30, second=0, microsecond=0)
        self.theater3 = Theater.objects.create(
            name='Cinepolis Bengaluru',
            movie=self.movie3,
            time=night_time,
            city='Bengaluru',
            theater_chain='Cinepolis',
            price=Decimal('180.00')
        )

        # Create seats
        self.seat1 = Seat.objects.create(theater=self.theater1, seat_number='A1', is_booked=False)
        self.seat2 = Seat.objects.create(theater=self.theater2, seat_number='B1', is_booked=False)

    def test_search_by_title_and_cast(self):
        """Test search by movie title and cast keywords."""
        url = reverse('movie_list')
        response = self.client.get(url, {'search': 'Interstellar'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)
        self.assertNotIn(self.movie2, movies)

        # Search by cast
        response = self.client.get(url, {'search': 'Keanu Matrix'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie2, movies)
        self.assertNotIn(self.movie1, movies)

    def test_filter_by_genre_and_language(self):
        """Test filtering by genre and language."""
        url = reverse('movie_list')
        
        # Genre filter
        response = self.client.get(url, {'genre': 'Sci-Fi'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)
        self.assertIn(self.movie4, movies)
        self.assertNotIn(self.movie3, movies)

        # Language filter
        response = self.client.get(url, {'language': 'Hindi'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie3, movies)
        self.assertNotIn(self.movie1, movies)

    def test_filter_by_city_and_theater(self):
        """Test filtering by city and theater venue."""
        url = reverse('movie_list')
        
        # City filter
        response = self.client.get(url, {'city': 'Mumbai'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)
        self.assertNotIn(self.movie3, movies)

        # Theater venue filter
        response = self.client.get(url, {'theater': 'PVR'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)

    def test_filter_by_rating(self):
        """Test filtering by minimum rating."""
        url = reverse('movie_list')
        response = self.client.get(url, {'rating': '8.5'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)
        self.assertIn(self.movie4, movies)
        self.assertNotIn(self.movie2, movies)

    def test_filter_by_show_timings(self):
        """Test filtering by morning, afternoon, evening, night show timings."""
        url = reverse('movie_list')
        
        # Morning timing (6am - 12pm)
        response = self.client.get(url, {'timing': 'morning'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie1, movies)
        self.assertNotIn(self.movie2, movies)

        # Evening timing (4pm - 8pm)
        response = self.client.get(url, {'timing': 'evening'})
        self.assertEqual(response.status_code, 200)
        movies = list(response.context['movies'])
        self.assertIn(self.movie2, movies)

    def test_sorting_options(self):
        """Test sorting by rating and newest."""
        url = reverse('movie_list')
        
        # Sort by rating (high to low)
        response = self.client.get(url, {'sort': 'rating'})
        self.assertEqual(response.status_code, 200)
        movies_in_context = list(response.context['movies'])
        # Highest rated should be first (Sci-Fi Chronicles 9.1, then Interstellar 8.9)
        self.assertEqual(movies_in_context[0].name, 'Sci-Fi Chronicles')
        self.assertEqual(movies_in_context[1].name, 'Interstellar Odyssey')

        # Sort by newest
        response = self.client.get(url, {'sort': 'newest'})
        self.assertEqual(response.status_code, 200)
        movies_in_context = list(response.context['movies'])
        self.assertEqual(movies_in_context[0].name, 'Sci-Fi Chronicles')

    def test_pagination(self):
        """Test pagination and query preservation."""
        url = reverse('movie_list')
        response = self.client.get(url, {'page': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('page_obj', response.context)
        self.assertEqual(response.context['total_matching_movies'], 4)

    def test_ajax_json_endpoint(self):
        """Test dynamic JSON response for live filtering without page reload."""
        url = reverse('movie_list')
        response = self.client.get(url, {'genre': 'Sci-Fi'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data['total_count'], 2)
        self.assertEqual(len(json_data['movies']), 2)

    def test_recommendation_engine_for_authenticated_user(self):
        """Test recommendation engine learns from user bookings."""
        # Book a Sci-Fi movie for self.user
        Booking.objects.create(
            user=self.user,
            seat=self.seat1,
            movie=self.movie1,
            theater=self.theater1
        )
        self.seat1.is_booked = True
        self.seat1.save()

        # Log in user
        self.client.force_login(self.user)
        url = reverse('movie_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Recommendations should prioritize unbooked Sci-Fi movies (like Sci-Fi Chronicles)
        rec_movies = response.context['recommended_movies']
        rec_names = [m.name for m in rec_movies]
        self.assertIn('Sci-Fi Chronicles', rec_names)
        self.assertNotIn('Interstellar Odyssey', rec_names)  # Already booked, should not recommend again

    def test_recommendation_fallback_for_guests(self):
        """Test recommendation fallback for guest users."""
        url = reverse('movie_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        rec_movies = response.context['recommended_movies']
        self.assertTrue(len(rec_movies) > 0)
        # Should include highest rated movies
        rec_names = [m.name for m in rec_movies]
        self.assertIn('Sci-Fi Chronicles', rec_names)


class TicketGenerationAndEmailTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='alice',
            password='password123',
            email='alice@example.com',
            first_name='Alice',
            last_name='Smith'
        )
        self.user2 = User.objects.create_user(
            username='bob',
            password='password123',
            email='bob@example.com',
            first_name='Bob',
            last_name='Jones'
        )

        self.movie = Movie.objects.create(
            name='Dune: Part Two',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('9.2'),
            release_date=datetime.date(2024, 3, 1),
            duration=166,
            cast='Timothée Chalamet, Zendaya',
            description='Paul Atreides unites with the Fremen people.'
        )

        self.theater = Theater.objects.create(
            name='PVR IMAX Lower Parel',
            movie=self.movie,
            time=timezone.now() + datetime.timedelta(days=1),
            city='Mumbai',
            screen_name='IMAX Laser Audi 1',
            price=Decimal('350.00')
        )

        self.seat1 = Seat.objects.create(theater=self.theater, seat_number='C1', is_booked=False)
        self.seat2 = Seat.objects.create(theater=self.theater, seat_number='C2', is_booked=False)
        self.seat3 = Seat.objects.create(theater=self.theater, seat_number='C3', is_booked=False)

    def test_pdf_ticket_generator_creates_valid_pdf(self):
        """Test ReportLab ticket generator outputs valid binary PDF with expected structure."""
        from .ticket_generator import generate_ticket_pdf
        
        booking = Booking.objects.create(
            user=self.user1,
            seat=self.seat1,
            movie=self.movie,
            theater=self.theater,
            total_price=self.theater.price,
            payment_status='CONFIRMED'
        )

        pdf_bytes = generate_ticket_pdf(booking)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 5000)
        # PDF magic number header check
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))

    def test_qr_code_generation(self):
        """Test that QR code generation generates a valid PIL image for verification payload."""
        from .ticket_generator import generate_qr_code_image
        
        payload = {
            "booking_id": "PMS-20260831-TEST01",
            "movie": "Dune: Part Two",
            "seats": ["C1", "C2"],
            "theater": "PVR IMAX Lower Parel"
        }
        qr_img = generate_qr_code_image(payload)
        self.assertIsNotNone(qr_img)
        self.assertTrue(qr_img.size[0] > 50)
        self.assertTrue(qr_img.size[1] > 50)

    def test_multi_seat_atomic_booking_flow(self):
        """Test selecting multiple seats books all atomically with unified booking_id."""
        self.client.force_login(self.user1)
        url = reverse('book_seats', kwargs={'theater_id': self.theater.id})
        
        response = self.client.post(url, {
            'seats': [self.seat1.id, self.seat2.id]
        })
        self.assertRedirects(response, reverse('profile'))

        # Verify both seats are marked booked
        self.seat1.refresh_from_db()
        self.seat2.refresh_from_db()
        self.assertTrue(self.seat1.is_booked)
        self.assertTrue(self.seat2.is_booked)

        # Check bookings created
        user_bookings = Booking.objects.filter(user=self.user1, theater=self.theater)
        self.assertEqual(user_bookings.count(), 2)

        # Ensure both share the identical booking_id and payment_reference
        booking_ids = set(user_bookings.values_list('booking_id', flat=True))
        payment_refs = set(user_bookings.values_list('payment_reference', flat=True))
        self.assertEqual(len(booking_ids), 1)
        self.assertEqual(len(payment_refs), 1)
        self.assertTrue(list(booking_ids)[0].startswith('PMS-'))

    def test_celery_email_task_execution(self):
        """Test asynchronous Celery email task executes and attaches PDF ticket."""
        from .tasks import send_ticket_email_task
        from django.core import mail

        booking = Booking.objects.create(
            user=self.user1,
            seat=self.seat1,
            movie=self.movie,
            theater=self.theater,
            total_price=self.theater.price,
        )

        result = send_ticket_email_task.apply(args=[booking.booking_id, self.user1.email])
        self.assertEqual(result.status, 'SUCCESS')
        self.assertEqual(result.result['status'], 'success')
        self.assertEqual(result.result['booking_id'], booking.booking_id)

        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn(booking.booking_id, sent_email.subject)
        self.assertIn(self.user1.email, sent_email.to)
        # Check that PDF attachment is included
        self.assertEqual(len(sent_email.attachments), 1)
        filename, content, mime_type = sent_email.attachments[0]
        self.assertTrue(filename.endswith('.pdf'))
        self.assertEqual(mime_type, 'application/pdf')
        self.assertTrue(content.startswith(b'%PDF-'))

        # Check email_sent status updated in DB
        booking.refresh_from_db()
        self.assertTrue(booking.email_sent)

    def test_download_ticket_authorized_and_unauthorized(self):
        """Test download endpoint enforces user ownership security."""
        booking = Booking.objects.create(
            user=self.user1,
            seat=self.seat1,
            movie=self.movie,
            theater=self.theater,
            total_price=self.theater.price
        )

        download_url = reverse('download_ticket', kwargs={'booking_id': booking.booking_id})

        # 1. Unauthenticated request should redirect to login
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 302)

        # 2. Authorized user (user1) can download PDF
        self.client.force_login(self.user1)
        response = self.client.get(download_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

        # 3. Unauthorized user (user2) is prevented from downloading
        self.client.force_login(self.user2)
        response = self.client.get(download_url)
        self.assertRedirects(response, reverse('profile'))

    def test_view_ticket_inline(self):
        """Test view ticket endpoint opens PDF inline in browser."""
        booking = Booking.objects.create(
            user=self.user1,
            seat=self.seat1,
            movie=self.movie,
            theater=self.theater,
            total_price=self.theater.price
        )

        self.client.force_login(self.user1)
        view_url = reverse('view_ticket', kwargs={'booking_id': booking.booking_id})
        response = self.client.get(view_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('inline;', response['Content-Disposition'])

    def test_resend_ticket_email_endpoint(self):
        """Test resend email endpoint triggers email redispatch."""
        from django.core import mail
        booking = Booking.objects.create(
            user=self.user1,
            seat=self.seat1,
            movie=self.movie,
            theater=self.theater,
            total_price=self.theater.price
        )

        self.client.force_login(self.user1)
        resend_url = reverse('resend_ticket_email', kwargs={'booking_id': booking.booking_id})
        response = self.client.get(resend_url)
        self.assertRedirects(response, reverse('profile'))


class MovieManagementTrailerReviewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()
        self.past_time = self.now - datetime.timedelta(days=2)
        self.future_time = self.now + datetime.timedelta(days=2)

        # Users
        self.viewer = User.objects.create_user(username='verified_watcher', password='password123', email='watcher@example.com')
        self.future_buyer = User.objects.create_user(username='future_buyer', password='password123', email='future@example.com')
        self.unbooked_user = User.objects.create_user(username='just_browsing', password='password123', email='browse@example.com')

        # Movie
        self.movie = Movie.objects.create(
            name='Cosmic Odyssey',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('8.5'),
            duration=150,
            age_certification='UA 13+',
            trailer_url='https://www.youtube.com/watch?v=zSWdZVtXT7E',
            director='Christopher Nolan',
            synopsis='A deep space exploration mission to discover habitability beyond the solar system.',
            release_date=datetime.date(2024, 3, 1),
            cast='Matthew McConaughey, Anne Hathaway'
        )

        # Theaters: Past & Future
        self.theater_past = Theater.objects.create(
            movie=self.movie,
            name='PVR Cinema Past Show',
            city='Mumbai',
            screen_name='Audi 1',
            theater_chain='PVR',
            time=self.past_time,
            price=Decimal('250.00')
        )
        self.theater_future = Theater.objects.create(
            movie=self.movie,
            name='INOX Future Show',
            city='Mumbai',
            screen_name='Audi 2',
            theater_chain='INOX',
            time=self.future_time,
            price=Decimal('300.00')
        )

        # Seats
        self.seat_past = Seat.objects.create(theater=self.theater_past, seat_number='C1', is_booked=True)
        self.seat_future = Seat.objects.create(theater=self.theater_future, seat_number='D1', is_booked=True)

        # Bookings: Verified watcher booked past show; Future buyer booked future show
        self.booking_past = Booking.objects.create(
            user=self.viewer,
            movie=self.movie,
            theater=self.theater_past,
            seat=self.seat_past,
            total_price=self.theater_past.price,
            payment_status='CONFIRMED'
        )
        self.booking_future = Booking.objects.create(
            user=self.future_buyer,
            movie=self.movie,
            theater=self.theater_future,
            seat=self.seat_future,
            total_price=self.theater_future.price,
            payment_status='CONFIRMED'
        )

    def test_youtube_trailer_id_extraction_and_embed_url(self):
        """Test secure extraction of YouTube 11-char ID and privacy-enhanced embed URL."""
        # Standard watch URL
        self.assertEqual(self.movie.get_youtube_video_id(), 'zSWdZVtXT7E')
        self.assertEqual(
            self.movie.get_youtube_embed_url(),
            'https://www.youtube-nocookie.com/embed/zSWdZVtXT7E?rel=0&modestbranding=1'
        )

        # Shortened youtu.be URL
        self.movie.trailer_url = 'https://youtu.be/Way9Dexny3w'
        self.assertEqual(self.movie.get_youtube_video_id(), 'Way9Dexny3w')

        # Embed URL
        self.movie.trailer_url = 'https://www.youtube.com/embed/Way9Dexny3w'
        self.assertEqual(self.movie.get_youtube_video_id(), 'Way9Dexny3w')

        # Shorts URL
        self.movie.trailer_url = 'https://youtube.com/shorts/Way9Dexny3w'
        self.assertEqual(self.movie.get_youtube_video_id(), 'Way9Dexny3w')

        # Raw 11-char ID
        self.movie.trailer_url = 'Way9Dexny3w'
        self.assertEqual(self.movie.get_youtube_video_id(), 'Way9Dexny3w')

        # Empty or None
        self.movie.trailer_url = None
        self.assertIsNone(self.movie.get_youtube_video_id())
        self.assertIsNone(self.movie.get_youtube_embed_url())

    def test_movie_cast_posters_and_metadata(self):
        """Test movie age certification, duration, cast members, and posters relations."""
        self.assertEqual(self.movie.age_certification, 'UA 13+')
        self.assertEqual(self.movie.duration, 150)
        self.assertEqual(self.movie.director, 'Christopher Nolan')

        # Cast member
        actor = CastMember.objects.create(
            movie=self.movie,
            name='Matthew McConaughey',
            role='Lead Actor',
            character_name='Cooper',
            order=0
        )
        self.assertEqual(self.movie.cast_members.count(), 1)
        self.assertIn('Cooper', str(actor))

        # Movie Poster
        poster = MoviePoster.objects.create(
            movie=self.movie,
            image='movies/posters/test.jpg',
            caption='IMAX Exclusive Poster',
            is_primary=True,
            order=1
        )
        self.assertEqual(self.movie.posters.count(), 1)
        self.assertTrue(poster.is_primary)

    def test_genres_and_languages_m2m(self):
        """Test Genre and Language models with slugify and M2M associations."""
        genre = Genre.objects.create(name='Science Fiction', icon='fa-rocket')
        self.assertEqual(genre.slug, 'science-fiction')

        language = Language.objects.create(name='English', code='en')
        self.movie.genres.add(genre)
        self.movie.languages.add(language)

        self.assertIn(genre, self.movie.genres.all())
        self.assertIn(language, self.movie.languages.all())

    def test_review_blocked_for_unauthenticated_user(self):
        """Test guests are redirected to login when attempting to submit a review."""
        review_url = reverse('submit_review', kwargs={'movie_id': self.movie.id})
        response = self.client.post(review_url, {
            'rating': '9',
            'headline': 'Great movie',
            'review_text': 'I loved this movie so much!'
        })
        self.assertRedirects(response, f"/login/?next={review_url}")
        self.assertEqual(Review.objects.filter(movie=self.movie).count(), 0)

    def test_review_blocked_for_user_without_booking(self):
        """Test authenticated user without any booking is blocked from reviewing."""
        self.client.force_login(self.unbooked_user)
        review_url = reverse('submit_review', kwargs={'movie_id': self.movie.id})
        response = self.client.post(review_url, {
            'rating': '8',
            'headline': 'Trying to review',
            'review_text': 'I never bought a ticket but want to review.'
        })
        self.assertRedirects(response, reverse('movie_detail', kwargs={'movie_id': self.movie.id}))
        self.assertEqual(Review.objects.filter(movie=self.movie, user=self.unbooked_user).count(), 0)

    def test_review_blocked_for_user_with_future_booking(self):
        """Test user with upcoming showtime cannot review until show has occurred."""
        self.client.force_login(self.future_buyer)
        review_url = reverse('submit_review', kwargs={'movie_id': self.movie.id})
        response = self.client.post(review_url, {
            'rating': '10',
            'headline': 'Excited for future show',
            'review_text': 'Reviewing ahead of time!'
        })
        self.assertRedirects(response, reverse('movie_detail', kwargs={'movie_id': self.movie.id}))
        self.assertEqual(Review.objects.filter(movie=self.movie, user=self.future_buyer).count(), 0)

    def test_review_allowed_for_verified_viewer_with_past_booking(self):
        """Test verified viewer who booked and attended screening can submit review."""
        self.client.force_login(self.viewer)
        review_url = reverse('submit_review', kwargs={'movie_id': self.movie.id})
        response = self.client.post(review_url, {
            'rating': '10',
            'headline': 'Masterpiece of modern cinema',
            'review_text': 'The visual effects and emotional depth were completely mindblowing.'
        })
        self.assertRedirects(response, f"/movies/{self.movie.id}/#reviews-section")

        review = Review.objects.get(movie=self.movie, user=self.viewer)
        self.assertEqual(review.rating, 10)
        self.assertTrue(review.is_verified_viewer)
        self.assertFalse(review.is_edited)
        self.assertEqual(review.booking, self.booking_past)

    def test_automatic_average_rating_calculation_and_editing(self):
        """Test system automatically calculates average rating across reviews and edits."""
        # 1. First review: 10 stars -> Movie rating becomes 10.0
        review1 = Review.objects.create(
            movie=self.movie,
            user=self.viewer,
            booking=self.booking_past,
            rating=10,
            headline='First review',
            review_text='Superb experience in theaters!',
            is_verified_viewer=True
        )
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.rating, Decimal('10.0'))

        # 2. Second user books past show and rates 8 stars -> Average becomes 9.0
        second_viewer = User.objects.create_user(username='viewer_two', password='pw2')
        seat2 = Seat.objects.create(theater=self.theater_past, seat_number='C2', is_booked=True)
        booking2 = Booking.objects.create(
            user=second_viewer,
            movie=self.movie,
            theater=self.theater_past,
            seat=seat2,
            total_price=self.theater_past.price,
            payment_status='CONFIRMED'
        )
        review2 = Review.objects.create(
            movie=self.movie,
            user=second_viewer,
            booking=booking2,
            rating=8,
            headline='Second review',
            review_text='Very solid movie.',
            is_verified_viewer=True
        )
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.rating, Decimal('9.0'))

        # 3. Edit review1 through endpoint: updates rating to 6 -> Average becomes (6 + 8)/2 = 7.0
        self.client.force_login(self.viewer)
        edit_url = reverse('submit_review', kwargs={'movie_id': self.movie.id})
        self.client.post(edit_url, {
            'rating': '6',
            'headline': 'Updated: Good but flawed',
            'review_text': 'Second watch was not as impactful.'
        })
        review1.refresh_from_db()
        self.assertEqual(review1.rating, 6)
        self.assertTrue(review1.is_edited)

        self.movie.refresh_from_db()
        self.assertEqual(self.movie.rating, Decimal('7.0'))

        # 4. Delete review2 -> Rating recalculates back to 6.0
        self.client.force_login(second_viewer)
        delete_url = reverse('delete_review', kwargs={'review_id': review2.id})
        self.client.post(delete_url)
        self.movie.refresh_from_db()
        self.assertEqual(self.movie.rating, Decimal('6.0'))
        self.assertEqual(Review.objects.filter(movie=self.movie).count(), 1)

    def test_review_reporting_workflow(self):
        """Test reporting inappropriate reviews and preventing self-reporting."""
        review = Review.objects.create(
            movie=self.movie,
            user=self.viewer,
            booking=self.booking_past,
            rating=1,
            headline='Inappropriate Review',
            review_text='Contains toxic and offensive language!',
            is_verified_viewer=True
        )

        report_url = reverse('report_review', kwargs={'review_id': review.id})

        # 1. Author cannot report their own review
        self.client.force_login(self.viewer)
        response = self.client.post(report_url, {'reason': 'OFFENSIVE', 'details': 'My own review'})
        self.assertEqual(ReviewReport.objects.count(), 0)

        # 2. Another user can report the review
        self.client.force_login(self.unbooked_user)
        response = self.client.post(report_url, {
            'reason': 'OFFENSIVE',
            'details': 'Uses vulgar language violating community rules.'
        })
        self.assertEqual(ReviewReport.objects.count(), 1)
        report = ReviewReport.objects.first()
        self.assertEqual(report.review, review)
        self.assertEqual(report.reported_by, self.unbooked_user)
        self.assertEqual(report.reason, 'OFFENSIVE')
        self.assertEqual(report.status, 'PENDING')

        # 3. Duplicate report by same user updates gracefully without crashing
        self.client.post(report_url, {'reason': 'SPAM', 'details': 'Updated reason to spam.'})
        self.assertEqual(ReviewReport.objects.count(), 1)
        report.refresh_from_db()
        self.assertEqual(report.reason, 'SPAM')

    def test_movie_detail_view_and_recommendations(self):
        """Test movie detail page loads successfully with similar, trending, and new releases."""
        # Create similar movie
        similar_movie = Movie.objects.create(
            name='Dune Odyssey',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('8.8'),
            duration=160
        )
        detail_url = reverse('movie_detail', kwargs={'movie_id': self.movie.id})
        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.movie.name)
        self.assertContains(response, 'UA 13+')
        self.assertContains(response, 'Christopher Nolan')
        self.assertContains(response, 'Watch Trailer')

        # Recommendations in context
        self.assertIn('similar_movies', response.context)
        self.assertIn('trending_movies', response.context)
        self.assertIn('recent_releases', response.context)
        self.assertTrue(any(m.id == similar_movie.id for m in response.context['similar_movies']))


class PaymentWorkflowAndBookingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='pay_user1',
            password='password123',
            email='pay_user1@example.com',
            first_name='Rahul',
            last_name='Verma'
        )
        self.user2 = User.objects.create_user(
            username='pay_user2',
            password='password123',
            email='pay_user2@example.com',
            first_name='Priya',
            last_name='Sharma'
        )

        self.movie = Movie.objects.create(
            name='Kalki 2898 AD',
            genre='Sci-Fi',
            language='Hindi',
            rating=Decimal('8.7'),
            release_date=datetime.date(2024, 6, 27),
            duration=180,
            cast='Prabhas, Amitabh Bachchan, Deepika Padukone',
            description='A modern avatar of Vishnu descends to protect the world.'
        )

        self.theater = Theater.objects.create(
            name='INOX Megaplex Inorbit Mall',
            movie=self.movie,
            time=timezone.now() + datetime.timedelta(days=2),
            city='Mumbai',
            screen_name='Screen 2 (Dolby Atmos)',
            price=Decimal('250.00')
        )

        self.seatA1 = Seat.objects.create(theater=self.theater, seat_number='A1', is_booked=False)
        self.seatA2 = Seat.objects.create(theater=self.theater, seat_number='A2', is_booked=False)
        self.seatA3 = Seat.objects.create(theater=self.theater, seat_number='A3', is_booked=False)

    def test_initiate_payment_creates_order_and_pending_transaction(self):
        """Test Step 1: Initiating payment atomically locks seats and creates PENDING PaymentTransaction."""
        self.client.force_login(self.user1)
        url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})

        response = self.client.post(url, json.dumps({
            'seats': [self.seatA1.id, self.seatA2.id]
        }), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['order_id'].startswith('order_'))
        self.assertEqual(data['amount'], 50000)  # 250.00 * 2 * 100 paise
        self.assertEqual(data['currency'], 'INR')
        self.assertEqual(data['seat_numbers'], 'A1, A2')

        # Verify transaction in database
        txn = PaymentTransaction.objects.get(order_id=data['order_id'])
        self.assertEqual(txn.status, 'PENDING')
        self.assertEqual(txn.user, self.user1)
        self.assertEqual(txn.amount, Decimal('500.00'))

        # Verify seats are temporarily reserved
        self.seatA1.refresh_from_db()
        self.seatA2.refresh_from_db()
        self.assertTrue(self.seatA1.is_booked)
        self.assertTrue(self.seatA2.is_booked)

    def test_concurrent_seat_booking_rejected(self):
        """Test concurrency protection: Second user cannot initiate payment on already locked seats."""
        self.client.force_login(self.user1)
        url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})

        # User 1 initiates payment for seat A1
        res1 = self.client.post(url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()['success'])

        # User 2 tries to initiate payment for seat A1 concurrently
        self.client.force_login(self.user2)
        res2 = self.client.post(url, json.dumps({'seats': [self.seatA1.id, self.seatA3.id]}), content_type='application/json')
        self.assertEqual(res2.status_code, 409)
        self.assertFalse(res2.json()['success'])
        self.assertIn('already booked', res2.json()['error'])

    def test_server_side_hmac_signature_verification_success(self):
        """Test Step 2: Valid HMAC SHA256 signature confirms bookings and updates transaction to SUCCESS."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']
        payment_id = 'pay_kalki_success_001'

        # Generate cryptographically valid HMAC SHA256 signature
        valid_signature = generate_payment_signature(order_id, payment_id)

        verify_url = reverse('verify_payment', kwargs={'theater_id': self.theater.id})
        verify_res = self.client.post(verify_url, json.dumps({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': valid_signature,
            'payment_method': 'UPI'
        }), content_type='application/json')

        self.assertEqual(verify_res.status_code, 200)
        data = verify_res.json()
        self.assertTrue(data['success'])

        # Verify transaction status in DB
        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'SUCCESS')
        self.assertEqual(txn.payment_id, payment_id)
        self.assertEqual(txn.signature, valid_signature)

        # Verify Booking created in DB
        bookings = Booking.objects.filter(booking_id=txn.booking_id)
        self.assertEqual(bookings.count(), 1)
        booking = bookings.first()
        self.assertEqual(booking.payment_status, 'PAID')
        self.assertEqual(booking.user, self.user1)
        self.assertEqual(booking.transaction, txn)

        # Seat remains booked
        self.seatA1.refresh_from_db()
        self.assertTrue(self.seatA1.is_booked)

    def test_server_side_hmac_signature_verification_tampered_fails(self):
        """Test Security: Tampered signature rejects verification, marks transaction FAILED, and releases seats."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA2.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']
        payment_id = 'pay_tampered_002'
        tampered_signature = 'fraudulent_tampered_signature_xyz123'

        verify_url = reverse('verify_payment', kwargs={'theater_id': self.theater.id})
        verify_res = self.client.post(verify_url, json.dumps({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': tampered_signature,
        }), content_type='application/json')

        self.assertEqual(verify_res.status_code, 400)
        self.assertFalse(verify_res.json()['success'])

        # Transaction marked as FAILED
        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'FAILED')
        self.assertEqual(txn.error_code, 'INVALID_SIGNATURE')

        # Reserved seats must be automatically released!
        self.seatA2.refresh_from_db()
        self.assertFalse(self.seatA2.is_booked)

        # No bookings created
        self.assertEqual(Booking.objects.filter(booking_id=txn.booking_id).count(), 0)

    def test_cancelled_payment_automatically_releases_reserved_seats(self):
        """Test Cancellation: User closing checkout modal releases seats and marks transaction CANCELLED."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA3.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']

        self.seatA3.refresh_from_db()
        self.assertTrue(self.seatA3.is_booked)

        cancel_url = reverse('cancel_payment', kwargs={'theater_id': self.theater.id})
        cancel_res = self.client.post(cancel_url, json.dumps({
            'order_id': order_id,
            'reason': 'User closed modal'
        }), content_type='application/json')

        self.assertEqual(cancel_res.status_code, 200)
        self.assertTrue(cancel_res.json()['success'])

        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'CANCELLED')

        # Reserved seats must be automatically released!
        self.seatA3.refresh_from_db()
        self.assertFalse(self.seatA3.is_booked)

    def test_idempotent_duplicate_payment_confirmation_prevents_duplicate_bookings(self):
        """Test Idempotency: Duplicate payment callbacks must never create duplicate bookings."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']
        payment_id = 'pay_idempotent_001'
        sig = generate_payment_signature(order_id, payment_id)

        verify_url = reverse('verify_payment', kwargs={'theater_id': self.theater.id})
        payload = json.dumps({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': sig
        })

        # 1st verification
        res1 = self.client.post(verify_url, payload, content_type='application/json')
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.json()['success'])
        self.assertEqual(Booking.objects.filter(seat=self.seatA1).count(), 1)

        # 2nd duplicate verification (e.g. user refreshed or callback re-sent)
        res2 = self.client.post(verify_url, payload, content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()['success'])
        self.assertTrue(res2.json().get('already_confirmed'))

        # Still exactly 1 booking - duplicate prevented!
        self.assertEqual(Booking.objects.filter(seat=self.seatA1).count(), 1)

    def test_server_side_webhook_signature_verification(self):
        """Test Webhook: Cryptographic signature verification accepts valid signature and rejects invalid."""
        url = reverse('payment_webhook')
        payload = json.dumps({'event': 'payment.captured', 'payload': {}})
        raw_body = payload.encode('utf-8')

        # Valid webhook signature
        import hmac, hashlib
        secret = get_razorpay_webhook_secret()
        valid_sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

        response_valid = self.client.post(url, data=raw_body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=valid_sig)
        self.assertEqual(response_valid.status_code, 200)

        # Invalid webhook signature
        response_invalid = self.client.post(url, data=raw_body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE='invalid_webhook_signature')
        self.assertEqual(response_invalid.status_code, 403)

    def test_webhook_payment_captured_confirms_booking_idempotently(self):
        """Test Webhook: Asynchronous payment.captured event confirms pending booking."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']

        webhook_url = reverse('payment_webhook')
        wh_payload = json.dumps({
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_webhook_cap_001',
                        'order_id': order_id,
                        'amount': 25000,
                        'status': 'captured'
                    }
                }
            }
        })
        raw_body = wh_payload.encode('utf-8')
        secret = get_razorpay_webhook_secret()
        import hmac, hashlib
        sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

        # Dispatch webhook
        wh_res = self.client.post(webhook_url, data=raw_body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=sig)
        self.assertEqual(wh_res.status_code, 200)

        # Verify transaction and booking created
        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'SUCCESS')
        self.assertEqual(Booking.objects.filter(booking_id=txn.booking_id).count(), 1)

        # Dispatch duplicate webhook
        wh_res2 = self.client.post(webhook_url, data=raw_body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=sig)
        self.assertEqual(wh_res2.status_code, 200)
        self.assertEqual(Booking.objects.filter(booking_id=txn.booking_id).count(), 1)

    def test_webhook_payment_failed_releases_seats(self):
        """Test Webhook: payment.failed event marks transaction FAILED and releases reserved seats."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA2.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']

        self.seatA2.refresh_from_db()
        self.assertTrue(self.seatA2.is_booked)

        webhook_url = reverse('payment_webhook')
        wh_payload = json.dumps({
            'event': 'payment.failed',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_failed_webhook_002',
                        'order_id': order_id,
                        'error_description': 'Bank connection timed out'
                    }
                }
            }
        })
        raw_body = wh_payload.encode('utf-8')
        secret = get_razorpay_webhook_secret()
        import hmac, hashlib
        sig = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()

        wh_res = self.client.post(webhook_url, data=raw_body, content_type='application/json', HTTP_X_RAZORPAY_SIGNATURE=sig)
        self.assertEqual(wh_res.status_code, 200)

        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'FAILED')

        # Seats released
        self.seatA2.refresh_from_db()
        self.assertFalse(self.seatA2.is_booked)

    def test_payment_retry_workflow_reclaims_available_seats(self):
        """Test Payment Retry: Retrying failed transaction when seats are free pre-selects them."""
        self.client.force_login(self.user1)
        txn = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-RETRY-001',
            order_id='order_retry_001',
            amount=Decimal('250.00'),
            status='FAILED',
            seat_ids=str(self.seatA1.id),
            seat_numbers='A1'
        )

        retry_url = reverse('retry_payment', kwargs={'transaction_id': txn.id})
        response = self.client.get(retry_url)
        expected_redirect = f"{reverse('book_seats', kwargs={'theater_id': self.theater.id})}?retry=1&seats={self.seatA1.id}"
        self.assertRedirects(response, expected_redirect)

    def test_payment_retry_fails_gracefully_if_seats_already_taken(self):
        """Test Payment Retry Edge Case: If another user booked the seats, user is alerted politely."""
        self.client.force_login(self.user1)
        txn = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-RETRY-002',
            order_id='order_retry_002',
            amount=Decimal('250.00'),
            status='FAILED',
            seat_ids=str(self.seatA1.id),
            seat_numbers='A1'
        )

        # In the meantime, another user booked seat A1
        self.seatA1.is_booked = True
        self.seatA1.save()

        retry_url = reverse('retry_payment', kwargs={'transaction_id': txn.id})
        response = self.client.get(retry_url, follow=True)
        self.assertContains(response, 'already been booked by another user')

    def test_profile_displays_full_payment_transaction_history(self):
        """Test Profile Audit Log: Profile renders complete booking history and transaction history."""
        self.client.force_login(self.user1)

        # Create successful transaction
        txn_success = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-AUDIT-SUCCESS',
            order_id='order_audit_success_1',
            payment_id='pay_audit_success_1',
            amount=Decimal('250.00'),
            status='SUCCESS',
            seat_ids=str(self.seatA1.id),
            seat_numbers='A1'
        )
        Booking.objects.create(
            user=self.user1,
            seat=self.seatA1,
            movie=self.movie,
            theater=self.theater,
            transaction=txn_success,
            booking_id=txn_success.booking_id,
            payment_reference=txn_success.payment_id,
            total_price=self.theater.price,
            payment_status='PAID'
        )

        # Create failed transaction
        txn_failed = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-AUDIT-FAILED',
            order_id='order_audit_failed_2',
            amount=Decimal('500.00'),
            status='FAILED',
            error_description='Card declined by issuing bank',
            seat_ids=f"{self.seatA2.id},{self.seatA3.id}",
            seat_numbers='A2, A3'
        )

        profile_url = reverse('profile')
        response = self.client.get(profile_url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('transactions', response.context)
        self.assertEqual(response.context['transactions'].count(), 2)

        # Check HTML renders both transactions and statuses
        self.assertContains(response, 'order_audit_success_1')
        self.assertContains(response, 'order_audit_failed_2')
        self.assertContains(response, 'Success')
        self.assertContains(response, 'Failed')
        self.assertContains(response, 'Retry')

    def test_payment_success_and_failed_views(self):
        """Test payment success receipt page and payment failed view rendering."""
        self.client.force_login(self.user1)

        txn = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-VIEW-TEST-001',
            order_id='order_view_test_001',
            payment_id='pay_view_test_001',
            amount=Decimal('250.00'),
            status='SUCCESS',
            seat_ids=str(self.seatA1.id),
            seat_numbers='A1'
        )
        Booking.objects.create(
            user=self.user1,
            seat=self.seatA1,
            movie=self.movie,
            theater=self.theater,
            transaction=txn,
            booking_id=txn.booking_id,
            payment_reference=txn.payment_id,
            total_price=self.theater.price,
            payment_status='PAID'
        )

        # Success view
        success_url = reverse('payment_success', kwargs={'booking_id': txn.booking_id})
        res_success = self.client.get(success_url)
        self.assertEqual(res_success.status_code, 200)
        self.assertContains(res_success, 'Payment Successful!')
        self.assertContains(res_success, txn.booking_id)

        # Failed view
        txn_fail = PaymentTransaction.objects.create(
            user=self.user1,
            movie=self.movie,
            theater=self.theater,
            booking_id='PMS-VIEW-TEST-002',
            order_id='order_view_test_002',
            amount=Decimal('250.00'),
            status='FAILED',
            error_description='Bank timeout error'
        )
        failed_url = reverse('payment_failed', kwargs={'transaction_id': txn_fail.id})
        res_fail = self.client.get(failed_url)
        self.assertEqual(res_fail.status_code, 200)
        self.assertContains(res_fail, 'Payment Not Completed')
        self.assertContains(res_fail, 'Seats Automatically Released')

    def test_payment_failed_view_releases_pending_seats_and_marks_failed(self):
        """Test Failure Handling: Accessing payment_failed with a PENDING transaction immediately releases seats and sets status to FAILED."""
        self.client.force_login(self.user1)

        # 1. Initiate payment to reserve seat A1
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']
        txn = PaymentTransaction.objects.get(order_id=order_id)
        self.assertEqual(txn.status, 'PENDING')

        self.seatA1.refresh_from_db()
        self.assertTrue(self.seatA1.is_booked)

        # 2. Simulate Razorpay checkout failure redirecting to payment_failed
        failed_url = f"{reverse('payment_failed', kwargs={'transaction_id': txn.id})}?error_code=BAD_REQUEST_ERROR&error_description=Card+declined+by+bank"
        res = self.client.get(failed_url)
        self.assertEqual(res.status_code, 200)

        # 3. Transaction MUST be transitioned to FAILED
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'FAILED')
        self.assertEqual(txn.error_code, 'BAD_REQUEST_ERROR')
        self.assertIn('Card declined', txn.error_description)

        # 4. Seat MUST be released in database (is_booked = False)
        self.seatA1.refresh_from_db()
        self.assertFalse(self.seatA1.is_booked)

        # 5. UI displays status as Failed (not Pending)
        self.assertContains(res, 'Failed')

    def test_release_stale_seat_holds_fifo_expiration(self):
        """Test FIFO & Hold Expiry: Abandoned checkout holds older than 5 minutes expire and free seats for the next user."""
        self.client.force_login(self.user1)

        # 1. User 1 initiates checkout for seat A2
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA2.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']
        txn = PaymentTransaction.objects.get(order_id=order_id)

        self.seatA2.refresh_from_db()
        self.assertTrue(self.seatA2.is_booked)

        # 2. Backdate transaction by 10 minutes to simulate abandoned checkout
        stale_time = timezone.now() - datetime.timedelta(minutes=10)
        PaymentTransaction.objects.filter(id=txn.id).update(created_at=stale_time)

        # 3. User 2 loads seat selection or initiates payment for seat A2
        self.client.force_login(self.user2)
        res_user2 = self.client.post(init_url, json.dumps({'seats': [self.seatA2.id]}), content_type='application/json')

        # Stale hold should have expired and User 2 gets the seat (FIFO queue!)
        self.assertEqual(res_user2.status_code, 200)
        self.assertTrue(res_user2.json()['success'])

        # Previous transaction marked as FAILED with HOLD_TIMEOUT_EXPIRED
        txn.refresh_from_db()
        self.assertEqual(txn.status, 'FAILED')
        self.assertEqual(txn.error_code, 'HOLD_TIMEOUT_EXPIRED')


class SmartSeatReservationTests(TestCase):
    """
    Comprehensive test suite for Task 4: Smart Seat Reservation with Live Availability.
    Validates:
    1. 2-minute temporary seat reservation lifecycle.
    2. Automatic expiration and seat release after 2 minutes.
    3. Multi-user concurrent reservation race-condition protection (serialized locks & 409 Conflict).
    4. Modification of seat selection before payment.
    5. Rejection of conflicting or already-held seats during modification.
    6. Explicit seat release API.
    7. Live seat availability endpoint with accurate statuses and remaining countdown timers.
    8. Successful payment converting temporary reservation into permanent booking.
    9. Checkout cancellation immediately restoring seat availability.
    """
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='res_alice', password='password123', email='alice@cinema.com')
        self.user2 = User.objects.create_user(username='res_bob', password='password123', email='bob@cinema.com')

        self.movie = Movie.objects.create(
            name='Avatar 3: Fire and Ash',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('9.2'),
            duration=190,
            cast='Sam Worthington, Zoe Saldana'
        )
        self.theater = Theater.objects.create(
            name='PVR IMAX Phoenix Marketcity',
            movie=self.movie,
            time=timezone.now() + datetime.timedelta(days=1),
            city='Mumbai',
            screen_name='Audi 1 (IMAX)',
            price=Decimal('400.00')
        )
        self.seatA1 = Seat.objects.create(theater=self.theater, seat_number='A1', is_booked=False)
        self.seatA2 = Seat.objects.create(theater=self.theater, seat_number='A2', is_booked=False)
        self.seatA3 = Seat.objects.create(theater=self.theater, seat_number='A3', is_booked=False)
        self.seatB1 = Seat.objects.create(theater=self.theater, seat_number='B1', is_booked=False)
        self.seatB2 = Seat.objects.create(theater=self.theater, seat_number='B2', is_booked=True)  # Already permanently booked

    def test_seat_reservation_success_for_two_minutes(self):
        """Test reserving seats temporarily locks them for 2 minutes with ownership tracking."""
        self.client.force_login(self.user1)
        url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})

        response = self.client.post(
            url,
            json.dumps({'seats': [self.seatA1.id, self.seatA2.id]}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['seat_count'], 2)
        self.assertEqual(data['remaining_seconds'], 120)
        self.assertEqual(data['total_amount'], 800.00)

        # Verify DB state
        self.seatA1.refresh_from_db()
        self.seatA2.refresh_from_db()
        self.assertEqual(self.seatA1.reserved_by, self.user1)
        self.assertEqual(self.seatA2.reserved_by, self.user1)
        self.assertFalse(self.seatA1.is_booked)
        self.assertFalse(self.seatA2.is_booked)
        self.assertTrue(self.seatA1.is_currently_reserved())
        self.assertFalse(self.seatA1.is_available())

        # Status for User 1 vs User 2
        self.assertEqual(self.seatA1.get_status(self.user1), 'reserved_by_you')
        self.assertEqual(self.seatA1.get_status(self.user2), 'reserved')
        self.assertGreater(self.seatA1.get_remaining_seconds(), 110)

    def test_seat_auto_release_after_two_minutes(self):
        """Test that temporary reservations older than 2 minutes are automatically expired and available."""
        self.client.force_login(self.user1)
        url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})

        # Reserve seat A1
        res = self.client.post(url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(res.status_code, 200)

        # Backdate reservation by 2 minutes + 5 seconds (125s ago) to simulate timeout
        expired_time = timezone.now() - datetime.timedelta(seconds=125)
        Seat.objects.filter(id=self.seatA1.id).update(reserved_until=expired_time)

        self.seatA1.refresh_from_db()
        self.assertFalse(self.seatA1.is_currently_reserved())
        self.assertTrue(self.seatA1.is_available())

        # User 2 attempts to reserve seat A1
        self.client.force_login(self.user2)
        res2 = self.client.post(url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.json()['success'])

        # Now owned by User 2
        self.seatA1.refresh_from_db()
        self.assertEqual(self.seatA1.reserved_by, self.user2)

    def test_concurrent_seat_reservation_race_condition(self):
        """Test multi-user concurrency: User 2 is rejected with HTTP 409 Conflict if attempting to reserve user 1's seats."""
        self.client.force_login(self.user1)
        url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})

        # User 1 reserves A1 and A2
        res1 = self.client.post(url, json.dumps({'seats': [self.seatA1.id, self.seatA2.id]}), content_type='application/json')
        self.assertEqual(res1.status_code, 200)

        # User 2 attempts to reserve A2 and A3
        self.client.force_login(self.user2)
        res2 = self.client.post(url, json.dumps({'seats': [self.seatA2.id, self.seatA3.id]}), content_type='application/json')
        self.assertEqual(res2.status_code, 409)
        self.assertFalse(res2.json()['success'])
        self.assertIn('A2', res2.json()['error'])
        self.assertIn('reserved by another user', res2.json()['error'])

        # Seat A3 was NOT reserved because transaction was atomic
        self.seatA3.refresh_from_db()
        self.assertTrue(self.seatA3.is_available())

    def test_modify_seat_selection_before_payment(self):
        """Test user can modify seat selection, atomically freeing deselected seats and locking new ones."""
        self.client.force_login(self.user1)
        res_url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})
        mod_url = reverse('modify_reservation_api', kwargs={'theater_id': self.theater.id})

        # 1. User 1 initially reserves A1 and A2
        self.client.post(res_url, json.dumps({'seats': [self.seatA1.id, self.seatA2.id]}), content_type='application/json')

        # 2. User 1 modifies selection to A2 and A3 (dropping A1, adding A3)
        res_mod = self.client.post(mod_url, json.dumps({'seats': [self.seatA2.id, self.seatA3.id]}), content_type='application/json')
        self.assertEqual(res_mod.status_code, 200)
        data = res_mod.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['seat_count'], 2)
        self.assertEqual(data['seat_ids'], [self.seatA2.id, self.seatA3.id])

        # 3. Seat A1 must be released immediately!
        self.seatA1.refresh_from_db()
        self.assertIsNone(self.seatA1.reserved_by)
        self.assertIsNone(self.seatA1.reserved_until)
        self.assertTrue(self.seatA1.is_available())

        # 4. Seats A2 and A3 are held by User 1
        self.seatA2.refresh_from_db()
        self.seatA3.refresh_from_db()
        self.assertEqual(self.seatA2.reserved_by, self.user1)
        self.assertEqual(self.seatA3.reserved_by, self.user1)

        # 5. User 2 can now immediately pick seat A1!
        self.client.force_login(self.user2)
        res_user2 = self.client.post(res_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(res_user2.status_code, 200)
        self.seatA1.refresh_from_db()
        self.assertEqual(self.seatA1.reserved_by, self.user2)

    def test_modify_seat_selection_rejects_conflicting_seats(self):
        """Test modifying selection rejects seats already held by others or permanently booked."""
        # User 2 reserves B1
        self.client.force_login(self.user2)
        res_url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})
        self.client.post(res_url, json.dumps({'seats': [self.seatB1.id]}), content_type='application/json')

        # User 1 has A1, tries to modify to include B1 (held by User 2) and B2 (booked)
        self.client.force_login(self.user1)
        self.client.post(res_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')

        mod_url = reverse('modify_reservation_api', kwargs={'theater_id': self.theater.id})
        res_mod = self.client.post(mod_url, json.dumps({'seats': [self.seatA1.id, self.seatB1.id]}), content_type='application/json')
        self.assertEqual(res_mod.status_code, 409)
        self.assertIn('B1', res_mod.json()['error'])

        # User 1 tries to include already permanently booked seat B2
        res_mod2 = self.client.post(mod_url, json.dumps({'seats': [self.seatA1.id, self.seatB2.id]}), content_type='application/json')
        self.assertEqual(res_mod2.status_code, 409)
        self.assertIn('booked', res_mod2.json()['error'].lower())

    def test_release_reservation_api(self):
        """Test explicit release API clears holds immediately."""
        self.client.force_login(self.user1)
        res_url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})
        rel_url = reverse('release_reservation_api', kwargs={'theater_id': self.theater.id})

        # Reserve A1, A2
        self.client.post(res_url, json.dumps({'seats': [self.seatA1.id, self.seatA2.id]}), content_type='application/json')

        # Explicit release
        res_rel = self.client.post(rel_url)
        self.assertEqual(res_rel.status_code, 200)
        self.assertTrue(res_rel.json()['success'])

        self.seatA1.refresh_from_db()
        self.seatA2.refresh_from_db()
        self.assertIsNone(self.seatA1.reserved_by)
        self.assertIsNone(self.seatA1.reserved_until)
        self.assertTrue(self.seatA1.is_available())

    def test_live_seat_availability_api(self):
        """Test live availability endpoint returns all seats with accurate statuses and remaining countdown timers."""
        # Hold A1 by User 1
        self.seatA1.reserved_by = self.user1
        self.seatA1.reserved_until = timezone.now() + datetime.timedelta(seconds=90)
        self.seatA1.save()

        # Hold A2 by User 2
        self.seatA2.reserved_by = self.user2
        self.seatA2.reserved_until = timezone.now() + datetime.timedelta(seconds=60)
        self.seatA2.save()

        self.client.force_login(self.user1)
        avail_url = reverse('seat_availability_api', kwargs={'theater_id': self.theater.id})
        res = self.client.get(avail_url)

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['theater_id'], self.theater.id)

        # Lookup seats by number
        seats_map = {s['seat_number']: s for s in data['seats']}
        self.assertEqual(seats_map['A1']['status'], 'reserved_by_you')
        self.assertGreater(seats_map['A1']['remaining_seconds'], 80)
        self.assertEqual(seats_map['A2']['status'], 'reserved')
        self.assertGreater(seats_map['A2']['remaining_seconds'], 50)
        self.assertEqual(seats_map['A3']['status'], 'available')
        self.assertEqual(seats_map['B2']['status'], 'booked')

        # User active reservation info
        self.assertTrue(data['user_reservation']['has_active_reservation'])
        self.assertIn(self.seatA1.id, data['user_reservation']['seat_ids'])

    def test_payment_verification_converts_reservation_to_confirmed_booking(self):
        """Test payment verification transitions temporary reservation to permanent booking (is_booked=True)."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        verify_url = reverse('verify_payment', kwargs={'theater_id': self.theater.id})

        # 1. Initiate payment for A1
        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(init_res.status_code, 200)
        order_id = init_res.json()['order_id']

        # 2. Verify payment with valid signature
        verify_res = self.client.post(verify_url, json.dumps({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': 'pay_test_smart_res_001',
            'razorpay_signature': 'simulated_valid_hmac_sha256'
        }), content_type='application/json')
        self.assertEqual(verify_res.status_code, 200)
        self.assertTrue(verify_res.json()['success'])

        # 3. Seat is now permanently booked
        self.seatA1.refresh_from_db()
        self.assertTrue(self.seatA1.is_booked)
        self.assertIsNone(self.seatA1.reserved_until)
        self.assertIsNone(self.seatA1.reserved_by)
        self.assertEqual(self.seatA1.get_status(), 'booked')

        # 4. Booking created
        booking = Booking.objects.get(seat=self.seatA1)
        self.assertEqual(booking.payment_status, 'PAID')
        self.assertEqual(booking.user, self.user1)

    def test_payment_cancellation_releases_reservation(self):
        """Test cancelling payment checkout immediately releases reserved seats."""
        self.client.force_login(self.user1)
        init_url = reverse('initiate_payment', kwargs={'theater_id': self.theater.id})
        cancel_url = reverse('cancel_payment', kwargs={'theater_id': self.theater.id})

        init_res = self.client.post(init_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        order_id = init_res.json()['order_id']

        # Cancel checkout
        cancel_res = self.client.post(cancel_url, json.dumps({
            'order_id': order_id,
            'reason': 'User changed mind'
        }), content_type='application/json')
        self.assertEqual(cancel_res.status_code, 200)
        self.assertTrue(cancel_res.json()['success'])

        # Seat is available again
        self.seatA1.refresh_from_db()
        self.assertFalse(self.seatA1.is_booked)
        self.assertIsNone(self.seatA1.reserved_until)
        self.assertIsNone(self.seatA1.reserved_by)
        self.assertIsNone(self.seatA1.reservation_token)
        self.assertTrue(self.seatA1.is_available())

    def test_reservation_token_session_binding(self):
        """Test cryptographic reservation_token session binding across reserve and modify."""
        self.client.force_login(self.user1)
        res_url = reverse('reserve_seats_api', kwargs={'theater_id': self.theater.id})

        # Reserve seats with auto-generated token
        res = self.client.post(res_url, json.dumps({'seats': [self.seatA1.id]}), content_type='application/json')
        self.assertEqual(res.status_code, 200)
        token = res.json().get('reservation_token')
        self.assertIsNotNone(token)
        self.assertTrue(token.startswith('tok_'))

        # DB has token
        self.seatA1.refresh_from_db()
        self.assertEqual(self.seatA1.reservation_token, token)
        self.assertEqual(self.seatA1.get_status(token=token), 'reserved_by_you')

        # Different token sees 'reserved'
        self.assertEqual(self.seatA1.get_status(token='tok_different_attacker'), 'reserved')

        # Modify with matching token succeeds
        mod_url = reverse('modify_reservation_api', kwargs={'theater_id': self.theater.id})
        mod_res = self.client.post(mod_url, json.dumps({
            'seats': [self.seatA1.id, self.seatA2.id],
            'reservation_token': token
        }), content_type='application/json')
        self.assertEqual(mod_res.status_code, 200)
        self.assertTrue(mod_res.json()['success'])

    def test_seat_availability_etag_versioning(self):
        """Test seat_availability_api ETag hash versioning returning modified: false when unchanged."""
        self.client.force_login(self.user1)
        avail_url = reverse('seat_availability_api', kwargs={'theater_id': self.theater.id})

        # Initial call returns version hash
        res1 = self.client.get(avail_url)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertTrue(data1['success'])
        version1 = data1.get('version')
        self.assertIsNotNone(version1)

        # Polling with same version when unchanged returns modified: false
        res2 = self.client.get(f"{avail_url}?v={version1}")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2['success'])
        self.assertFalse(data2['modified'])
        self.assertEqual(data2['version'], version1)

        # Changing seat state invalidates ETag and sends modified: true with new data
        self.seatA1.is_booked = True
        self.seatA1.save()

        res3 = self.client.get(f"{avail_url}?v={version1}")
        self.assertEqual(res3.status_code, 200)
        data3 = res3.json()
        self.assertTrue(data3['success'])
        self.assertTrue(data3.get('modified', True))
        self.assertNotEqual(data3['version'], version1)

    def test_management_command_release_expired_seats(self):
        """Test release_expired_seats Django management command clears expired reservations."""
        from django.core.management import call_command
        from io import StringIO

        # Create expired hold on seat A1
        self.seatA1.reserved_by = self.user1
        self.seatA1.reserved_until = timezone.now() - datetime.timedelta(minutes=3)
        self.seatA1.reservation_token = 'tok_expired_001'
        self.seatA1.save()

        # Run command
        out = StringIO()
        call_command('release_expired_seats', theater_id=self.theater.id, stdout=out)
        output_str = out.getvalue()
        self.assertIn('Successfully released', output_str)

        # Seat A1 is freed
        self.seatA1.refresh_from_db()
        self.assertIsNone(self.seatA1.reserved_by)
        self.assertIsNone(self.seatA1.reserved_until)
        self.assertIsNone(self.seatA1.reservation_token)
        self.assertTrue(self.seatA1.is_available())

    def test_book_seats_view_populates_seat_rows(self):
        """Test book_seats GET view populates seat_rows row-by-row structure in context."""
        self.client.force_login(self.user1)
        url = reverse('book_seats', kwargs={'theater_id': self.theater.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('seat_rows', response.context)
        seat_rows = response.context['seat_rows']
        self.assertIn('A', seat_rows)
        self.assertIn('B', seat_rows)
        # Row A contains seats A1, A2, A3
        row_a_nums = [s.seat_number for s in seat_rows['A']]
        self.assertIn('A1', row_a_nums)
        self.assertIn('A2', row_a_nums)
        self.assertIn('A3', row_a_nums)


# ══════════════════════════════════════════════════════════════════════════════
# TASK 5: ADMIN DASHBOARD, REAL-TIME ANALYTICS & CSV EXPORT TEST SUITE
# ══════════════════════════════════════════════════════════════════════════════

class AdminDashboardAnalyticsTests(TestCase):
    """
    Comprehensive test suite for Task 5 covering:
    - Access control and role-based permissions (is_staff / is_superuser)
    - Real-time revenue aggregations (daily, weekly, monthly, yearly, filtered)
    - Booking trends time-series analysis (TruncDate)
    - Theater auditorium occupancy percentage calculations
    - Most booked movies rankings and ticket volumes
    - Top performing theaters by revenue and attendance
    - Peak booking hours distribution (ExtractHour)
    - Cancellation and refund statistics
    - Custom date range filtering and presets
    - CSV export reports (Revenue, Theaters, Movies, Bookings ledger)
    """

    def setUp(self):
        self.client = Client()
        self.regular_user = User.objects.create_user(
            username='regular_customer',
            password='password123',
            email='customer@example.com'
        )
        self.staff_user = User.objects.create_user(
            username='theater_manager',
            password='password123',
            email='manager@example.com',
            is_staff=True
        )
        self.super_user = User.objects.create_superuser(
            username='executive_admin',
            password='password123',
            email='admin@example.com'
        )

        now = timezone.now()
        self.now = now
        self.today = now.date()

        # Create Movies
        self.movie1 = Movie.objects.create(
            name='Cosmic Odyssey',
            genre='Sci-Fi',
            language='English',
            rating=Decimal('9.2'),
            release_date=datetime.date(2025, 1, 1),
            duration=160,
            cast='Astronaut John'
        )
        self.movie2 = Movie.objects.create(
            name='Summer Vibes',
            genre='Comedy',
            language='Hindi',
            rating=Decimal('8.1'),
            release_date=datetime.date(2025, 2, 1),
            duration=115,
            cast='Comedian Ravi'
        )

        # Create Theaters
        self.theater1 = Theater.objects.create(
            name='PVR Gold Class Mumbai',
            movie=self.movie1,
            time=now,
            city='Mumbai',
            theater_chain='PVR',
            price=Decimal('200.00'),
            screen_name='Screen 1'
        )
        self.theater2 = Theater.objects.create(
            name='INOX Laser Delhi',
            movie=self.movie2,
            time=now,
            city='Delhi-NCR',
            theater_chain='INOX',
            price=Decimal('300.00'),
            screen_name='Audi 2'
        )
        # Empty theater with 0 seats for division-by-zero testing
        self.theater3 = Theater.objects.create(
            name='Empty Screen Cine',
            movie=self.movie1,
            time=now,
            city='Pune',
            price=Decimal('150.00'),
            screen_name='Audi 3'
        )

        # Create Seats
        self.seat1 = Seat.objects.create(theater=self.theater1, seat_number='A1', is_booked=True)
        self.seat2 = Seat.objects.create(theater=self.theater1, seat_number='A2', is_booked=True)
        self.seat3 = Seat.objects.create(theater=self.theater1, seat_number='A3', is_booked=False)
        self.seat4 = Seat.objects.create(theater=self.theater1, seat_number='A4', is_booked=False)

        self.seat5 = Seat.objects.create(theater=self.theater2, seat_number='B1', is_booked=True)
        self.seat6 = Seat.objects.create(theater=self.theater2, seat_number='B2', is_booked=False)

        # Create Bookings
        # Booking 1: Today, CONFIRMED (₹200)
        self.booking1 = Booking.objects.create(
            user=self.regular_user,
            seat=self.seat1,
            movie=self.movie1,
            theater=self.theater1,
            booking_id='PMS-TEST-001',
            total_price=Decimal('200.00'),
            payment_status='CONFIRMED',
        )
        # Booking 2: 3 days ago, PAID (₹200)
        self.booking2 = Booking.objects.create(
            user=self.regular_user,
            seat=self.seat2,
            movie=self.movie1,
            theater=self.theater1,
            booking_id='PMS-TEST-002',
            total_price=Decimal('200.00'),
            payment_status='PAID',
        )
        # Booking 3: 10 days ago, CANCELLED (₹300)
        self.booking3 = Booking.objects.create(
            user=self.staff_user,
            seat=self.seat5,
            movie=self.movie2,
            theater=self.theater2,
            booking_id='PMS-TEST-003',
            total_price=Decimal('300.00'),
            payment_status='CANCELLED',
        )

        # Bypass auto_now_add by applying update directly to database
        Booking.objects.filter(id=self.booking2.id).update(booked_at=now - datetime.timedelta(days=3))
        Booking.objects.filter(id=self.booking3.id).update(booked_at=now - datetime.timedelta(days=10))

        # Create Transactions
        self.txn1 = PaymentTransaction.objects.create(
            user=self.regular_user,
            booking_id='PMS-TEST-001',
            movie=self.movie1,
            theater=self.theater1,
            gateway='RAZORPAY',
            order_id='order_dash_test_1',
            amount=Decimal('200.00'),
            status='SUCCESS',
            seat_numbers='A1',
            seat_ids=str(self.seat1.id),
        )
        self.txn2 = PaymentTransaction.objects.create(
            user=self.staff_user,
            booking_id='PMS-TEST-003',
            movie=self.movie2,
            theater=self.theater2,
            gateway='RAZORPAY',
            order_id='order_dash_test_3',
            amount=Decimal('50.00'),
            status='REFUNDED',
            seat_numbers='B1',
            seat_ids=str(self.seat5.id),
        )
        PaymentTransaction.objects.filter(id=self.txn2.id).update(created_at=now - datetime.timedelta(days=10))

    # 1. Access Control Tests
    def test_admin_dashboard_anonymous_redirect(self):
        """Anonymous user is redirected to login page when attempting to access admin dashboard."""
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_admin_dashboard_forbidden_for_regular_user(self):
        """Authenticated non-staff user receives HTTP 403 Forbidden with clear access denied message."""
        self.client.force_login(self.regular_user)
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'403', response.content)
        self.assertIn(b'Administrator Access Required', response.content)

    def test_admin_dashboard_access_for_staff(self):
        """Staff user (is_staff=True) receives HTTP 200 and loads admin dashboard template."""
        self.client.force_login(self.staff_user)
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'movies/admin_dashboard.html')
        self.assertIn('revenue_metrics', response.context)
        self.assertIn('occupancy', response.context)
        self.assertIn('trends_json', response.context)

    def test_admin_dashboard_access_for_superuser(self):
        """Superuser receives HTTP 200 on both direct and alias admin dashboard routes."""
        self.client.force_login(self.super_user)
        for url_name in ['admin_dashboard', 'root_admin_dashboard']:
            response = self.client.get(reverse(url_name))
            self.assertEqual(response.status_code, 200)

    # 2. Analytics Engine Unit Tests
    def test_revenue_metrics_calculations(self):
        """Validates daily, weekly, monthly, yearly, and filtered revenue calculations."""
        service = DashboardAnalyticsService()
        metrics = service.get_revenue_metrics()

        # Booking 1 is today (₹200)
        self.assertEqual(Decimal(str(metrics['daily_revenue'])), Decimal('200.00'))
        self.assertEqual(metrics['daily_bookings'], 1)

        # Booking 1 (today, ₹200) + Booking 2 (3 days ago, ₹200) = ₹400 in last 7 days
        self.assertEqual(Decimal(str(metrics['weekly_revenue'])), Decimal('400.00'))
        self.assertEqual(metrics['weekly_bookings'], 2)

        # Filtered revenue should match confirmed bookings
        self.assertEqual(Decimal(str(metrics['filtered_revenue'])), Decimal('400.00'))
        self.assertEqual(metrics['filtered_bookings'], 2)
        self.assertEqual(Decimal(str(metrics['avg_ticket_value'])), Decimal('200.00'))

    def test_booking_trends_time_series(self):
        """Validates daily grouping via TruncDate returning synchronized labels and revenue."""
        service = DashboardAnalyticsService()
        trends = service.get_booking_trends()

        self.assertIn('labels', trends)
        self.assertIn('bookings_data', trends)
        self.assertIn('revenue_data', trends)
        self.assertGreater(len(trends['labels']), 0)
        self.assertEqual(len(trends['labels']), len(trends['bookings_data']))
        self.assertEqual(len(trends['labels']), len(trends['revenue_data']))

    def test_theater_occupancy_percentage_calculation(self):
        """Validates occupancy formula (booked / total * 100) and zero-seat division safety."""
        service = DashboardAnalyticsService()
        occupancy = service.get_theater_occupancy_report()

        # Theater 1: 2 booked / 4 total = 50.0%
        t1_report = next((t for t in occupancy['theaters'] if t.id == self.theater1.id), None)
        self.assertIsNotNone(t1_report)
        self.assertEqual(t1_report.total_seats, 4)
        self.assertEqual(t1_report.booked_seats, 2)
        self.assertEqual(round(t1_report.occupancy_pct, 1), 50.0)

        # Theater 3: 0 seats -> occupancy should be 0.0% without error
        t3_report = next((t for t in occupancy['theaters'] if t.id == self.theater3.id), None)
        if t3_report:
            self.assertEqual(t3_report.occupancy_pct, 0.0)

        # Network average occupancy: 3 booked / 6 total seats = 50.0%
        self.assertEqual(occupancy['total_capacity'], 6)
        self.assertEqual(occupancy['total_booked'], 3)
        self.assertEqual(occupancy['network_occupancy_pct'], 50.0)

    def test_peak_booking_hours_distribution(self):
        """Validates 24-hour booking distribution array and peak hour detection."""
        service = DashboardAnalyticsService()
        peak_hours = service.get_peak_booking_hours()

        self.assertEqual(len(peak_hours['labels']), 24)
        self.assertEqual(len(peak_hours['counts']), 24)
        self.assertEqual(len(peak_hours['revenues']), 24)
        self.assertIn(':', peak_hours['peak_hour_label'])

    def test_cancellation_and_refund_statistics(self):
        """Validates cancellation rate %, refunded amounts, and net revenue."""
        service = DashboardAnalyticsService()
        stats = service.get_cancellation_and_refund_stats()

        # Total bookings = 3, Cancelled = 1 -> Cancellation rate = 33.33%
        self.assertEqual(stats['total_bookings'], 3)
        self.assertEqual(stats['confirmed_bookings'], 2)
        self.assertEqual(stats['cancelled_bookings'], 1)
        self.assertAlmostEqual(stats['cancellation_rate'], 33.33, places=1)

        # Refunded amount = ₹50, Gross revenue = ₹400 -> Net revenue = ₹350
        self.assertEqual(Decimal(str(stats['refunded_amount'])), Decimal('50.00'))
        self.assertEqual(Decimal(str(stats['net_revenue'])), Decimal('350.00'))

    def test_most_booked_movies_ranking(self):
        """Validates movies ranked by booking count in descending order."""
        service = DashboardAnalyticsService()
        movies_data = service.get_most_booked_movies(limit=10)

        self.assertGreaterEqual(len(movies_data['movies']), 1)
        top_movie = movies_data['movies'][0]
        # Movie 1 has 2 confirmed bookings
        self.assertEqual(top_movie.id, self.movie1.id)
        self.assertEqual(top_movie.booking_count, 2)

    def test_custom_date_range_filtering(self):
        """Validates custom start_date and end_date filtering excludes outside records."""
        # Query only today
        service_today = DashboardAnalyticsService(
            start_date=self.today.strftime('%Y-%m-%d'),
            end_date=self.today.strftime('%Y-%m-%d')
        )
        metrics_today = service_today.get_revenue_metrics()
        # Only Booking 1 was booked today (₹200)
        self.assertEqual(Decimal(str(metrics_today['filtered_revenue'])), Decimal('200.00'))
        self.assertEqual(metrics_today['filtered_bookings'], 1)

    def test_date_presets_in_dashboard_view(self):
        """Validates presets query parameter in admin_dashboard view."""
        self.client.force_login(self.super_user)
        for preset in ['today', '7d', '30d', 'month', 'year', 'all']:
            response = self.client.get(f"{reverse('admin_dashboard')}?preset={preset}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['active_preset'], preset)

    # 3. CSV Export Tests
    def test_export_revenue_csv(self):
        """Tests revenue summary CSV export headers and data rows."""
        self.client.force_login(self.super_user)
        url = reverse('export_revenue_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment; filename="pickmyshow_revenue_report_', response['Content-Disposition'])
        content = response.content.decode('utf-8')
        self.assertIn('PICKMYSHOW EXECUTIVE REVENUE & BUSINESS INTELLIGENCE REPORT', content)
        self.assertIn('Daily Revenue (Today)', content)
        self.assertIn('Net Revenue (Gross - Refunds)', content)

    def test_export_theaters_csv(self):
        """Tests theater occupancy CSV export headers and data."""
        self.client.force_login(self.super_user)
        url = reverse('export_theaters_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('PICKMYSHOW THEATER PERFORMANCE & OCCUPANCY REPORT', content)
        self.assertIn('PVR Gold Class Mumbai', content)
        self.assertIn('50.0%', content)

    def test_export_movies_csv(self):
        """Tests movies ranking CSV export headers and data."""
        self.client.force_login(self.super_user)
        url = reverse('export_movies_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('PICKMYSHOW MOVIE BOOKINGS & REVENUE REPORT', content)
        self.assertIn('Cosmic Odyssey', content)

    def test_export_bookings_csv(self):
        """Tests granular bookings transaction ledger CSV export."""
        self.client.force_login(self.super_user)
        url = reverse('export_bookings_csv')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('PICKMYSHOW GRANULAR BOOKINGS TRANSACTION LEDGER', content)
        self.assertIn('PMS-TEST-001', content)

    def test_csv_exports_forbidden_for_non_admin(self):
        """Ensures non-admin users cannot download CSV reports."""
        self.client.force_login(self.regular_user)
        for ep in ['export_revenue_csv', 'export_theaters_csv', 'export_movies_csv', 'export_bookings_csv']:
            response = self.client.get(reverse(ep))
            self.assertEqual(response.status_code, 403)









