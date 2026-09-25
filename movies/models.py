import re
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    icon = models.CharField(max_length=50, blank=True, default='fa-film', help_text="FontAwesome icon name e.g. fa-film, fa-fire, fa-laugh")
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Language(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, blank=True, help_text="ISO code e.g. en, hi, ta, te")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Movie(models.Model):
    GENRE_CHOICES = [
        ('Action', 'Action'),
        ('Comedy', 'Comedy'),
        ('Drama', 'Drama'),
        ('Sci-Fi', 'Sci-Fi'),
        ('Horror', 'Horror'),
        ('Romance', 'Romance'),
        ('Thriller', 'Thriller'),
        ('Adventure', 'Adventure'),
        ('Animation', 'Animation'),
        ('Fantasy', 'Fantasy'),
        ('Crime', 'Crime'),
        ('Mystery', 'Mystery'),
    ]

    LANGUAGE_CHOICES = [
        ('English', 'English'),
        ('Hindi', 'Hindi'),
        ('Tamil', 'Tamil'),
        ('Telugu', 'Telugu'),
        ('Malayalam', 'Malayalam'),
        ('Kannada', 'Kannada'),
        ('Spanish', 'Spanish'),
        ('French', 'French'),
    ]

    CERTIFICATION_CHOICES = [
        ('U', 'U (Universal - All Ages)'),
        ('UA 7+', 'UA 7+ (Parental Guidance for under 7)'),
        ('UA 13+', 'UA 13+ (Parental Guidance for under 13)'),
        ('UA 16+', 'UA 16+ (Parental Guidance for under 16)'),
        ('A', 'A (Adults Only 18+)'),
        ('PG-13', 'PG-13 (Parents Strongly Cautioned)'),
        ('R', 'R (Restricted 17+)'),
    ]

    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to="movies/")
    rating = models.DecimalField(max_digits=3, decimal_places=1)
    cast = models.TextField()
    description = models.TextField(blank=True, null=True)  # optional
    synopsis = models.TextField(blank=True, null=True, help_text="Detailed storyline and synopsis")
    director = models.CharField(max_length=255, blank=True, null=True, help_text="Director name")
    genre = models.CharField(max_length=100, choices=GENRE_CHOICES, default='Action')
    genres = models.ManyToManyField(Genre, blank=True, related_name='movies', help_text="Associated genre categories")
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, default='English')
    languages = models.ManyToManyField(Language, blank=True, related_name='movies', help_text="Available languages")
    age_certification = models.CharField(max_length=10, choices=CERTIFICATION_CHOICES, default='UA 13+', help_text="Censor rating / age certification")
    trailer_url = models.URLField(max_length=500, blank=True, null=True, help_text="YouTube trailer URL e.g. https://www.youtube.com/watch?v=... or embed link")
    release_date = models.DateField(null=True, blank=True)
    duration = models.PositiveIntegerField(default=120, help_text="Duration in minutes")
    views_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name

    def get_youtube_video_id(self):
        """Extracts 11-character YouTube video ID safely from multiple URL variants."""
        if not self.trailer_url:
            return None
        url = self.trailer_url.strip()
        if len(url) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        patterns = [
            r'(?:v=|\/embed\/|\/17\/|\/v\/|youtu\.be\/|\/shorts\/|\/watch\?v=)([\w-]{11})',
            r'^([\w-]{11})$'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_youtube_embed_url(self):
        """Returns privacy-enhanced, secure YouTube embed URL."""
        video_id = self.get_youtube_video_id()
        if video_id:
            return f"https://www.youtube-nocookie.com/embed/{video_id}?rel=0&modestbranding=1"
        return None

    def update_average_rating(self):
        """Recalculates and stores the average rating from verified reviews."""
        result = self.reviews.aggregate(avg_rating=models.Avg('rating'))
        avg_val = result.get('avg_rating')
        if avg_val is not None:
            self.rating = Decimal(str(round(avg_val, 1)))
            self.save(update_fields=['rating'])
        return self.rating

    def get_reviews_count(self):
        return self.reviews.count()

    def get_rating_breakdown(self):
        """Returns distribution and percentages across rating scores 1 to 10 via single-query aggregation."""
        rating_counts = dict(self.reviews.values_list('rating').annotate(cnt=models.Count('id')))
        total = sum(rating_counts.values())
        breakdown = {}
        for score in range(10, 0, -1):
            count = rating_counts.get(score, 0)
            pct = round((count / total) * 100) if total > 0 else 0
            breakdown[score] = {'count': count, 'percent': pct}
        return breakdown

    def get_similar_movies(self, limit=4):
        """Returns similar movies based on genre and language."""
        similar = Movie.objects.filter(
            models.Q(genre__iexact=self.genre) | models.Q(language__iexact=self.language)
        ).exclude(id=self.id).order_by('-rating', '-views_count')[:limit]
        return list(similar)

    def get_primary_poster(self):
        """Returns primary poster image or main movie image."""
        primary = self.posters.filter(is_primary=True).first()
        if primary and primary.image:
            return primary.image.url
        if self.image:
            return self.image.url
        return None

class Theater(models.Model):
    CITY_CHOICES = [
        ('Mumbai', 'Mumbai'),
        ('Delhi-NCR', 'Delhi-NCR'),
        ('Bengaluru', 'Bengaluru'),
        ('Hyderabad', 'Hyderabad'),
        ('Chennai', 'Chennai'),
        ('Kolkata', 'Kolkata'),
        ('Pune', 'Pune'),
        ('Ahmedabad', 'Ahmedabad'),
    ]

    name = models.CharField(max_length=255)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='theaters')
    time = models.DateTimeField()
    city = models.CharField(max_length=100, choices=CITY_CHOICES, default='Mumbai')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=200.00)
    theater_chain = models.CharField(max_length=100, blank=True, null=True)
    screen_name = models.CharField(max_length=100, default='Screen 1 (Audi 1)', help_text="Auditorium or screen name")

    class Meta:
        ordering = ['time']
        indexes = [
            models.Index(fields=['movie', 'price'], name='thtr_movie_price_idx'),
            models.Index(fields=['movie', 'time'], name='thtr_movie_time_idx'),
            models.Index(fields=['city', 'time'], name='thtr_city_time_idx'),
        ]

    def __str__(self):
        return f'{self.name} ({self.city}) - {self.movie.name} at {self.time.strftime("%d %b %I:%M %p") if self.time else ""}'

# Temporary Seat Hold Expiry Timeout (2 Minutes = 120 Seconds)
SEAT_RESERVATION_TIMEOUT_SECONDS = 120


class Seat(models.Model):
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.CharField(max_length=10)
    is_booked = models.BooleanField(default=False)
    reserved_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Temporary reservation expiry timestamp (auto-released after 2 minutes if unconfirmed)"
    )
    reserved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reserved_seats',
        help_text="User holding active temporary reservation"
    )
    reservation_token = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        db_index=True,
        help_text="Cryptographic UUID4 reservation session token binding"
    )

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['theater', 'is_booked'], name='seat_theater_booked_idx'),
        ]

    def __str__(self):
        return f'{self.seat_number} in {self.theater.name}'

    def is_currently_reserved(self):
        """Returns True if the seat is held under an active 2-minute temporary reservation."""
        from django.utils import timezone
        return bool(not self.is_booked and self.reserved_until and self.reserved_until > timezone.now())

    def is_available(self):
        """Returns True if the seat is neither permanently booked nor under an active temporary hold."""
        return not self.is_booked and not self.is_currently_reserved()

    def get_status(self, user=None, token=None):
        """
        Returns seat status string for UI and API serialization:
        - 'booked': Permanently booked / sold out
        - 'reserved_by_you': Held by the requesting user or matching reservation token
        - 'reserved': Temporarily held by another user (< 2 minutes)
        - 'available': Open for selection and reservation
        """
        if self.is_booked:
            return 'booked'
        if self.is_currently_reserved():
            if token and self.reservation_token == token:
                return 'reserved_by_you'
            if user and user.is_authenticated and self.reserved_by_id == user.id:
                return 'reserved_by_you'
            return 'reserved'
        return 'available'

    def get_remaining_seconds(self):
        """Returns remaining hold time in seconds or 0 if expired/available."""
        from django.utils import timezone
        if self.is_currently_reserved():
            diff = (self.reserved_until - timezone.now()).total_seconds()
            return max(0, int(diff))
        return 0


def generate_booking_id():
    import uuid
    from django.utils import timezone
    date_part = timezone.now().strftime('%Y%m%d')
    random_part = uuid.uuid4().hex[:6].upper()
    return f"PMS-{date_part}-{random_part}"

def generate_payment_reference():
    import uuid
    random_part = uuid.uuid4().hex[:10].upper()
    return f"PAY-PMS-{random_part}"


class PaymentTransaction(models.Model):
    GATEWAY_CHOICES = [
        ('RAZORPAY', 'Razorpay'),
        ('STRIPE', 'Stripe'),
    ]
    STATUS_CHOICES = [
        ('INITIATED', 'Initiated'),
        ('PENDING', 'Pending'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_transactions')
    booking_id = models.CharField(max_length=50, db_index=True, help_text="Unique booking ID reference code (e.g. PMS-2026-XXXXX)")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='payment_transactions')
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE, related_name='payment_transactions')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='RAZORPAY')
    order_id = models.CharField(max_length=100, unique=True, db_index=True, help_text="Gateway Order ID (e.g. order_xxxx)")
    payment_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Gateway Transaction ID (e.g. pay_xxxx)")
    signature = models.CharField(max_length=255, blank=True, null=True, help_text="Cryptographic HMAC SHA256 signature from gateway")
    reservation_token = models.CharField(max_length=64, blank=True, null=True, db_index=True, help_text="Reservation session token tied to this checkout")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total payment amount in INR (₹)")
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='INITIATED', db_index=True)
    seat_numbers = models.CharField(max_length=255, help_text="Comma-separated seat numbers (e.g. C1, C2)")
    seat_ids = models.CharField(max_length=255, help_text="Comma-separated seat IDs for automatic release on failure")
    payment_method = models.CharField(max_length=50, blank=True, null=True, default='UPI/Card/Netbanking', help_text="Payment mode")
    error_code = models.CharField(max_length=100, blank=True, null=True)
    error_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment Transaction'
        verbose_name_plural = 'Payment Transactions'
        indexes = [
            models.Index(fields=['status', 'created_at'], name='paytxn_status_date_idx'),
            models.Index(fields=['created_at'], name='paytxn_created_idx'),
        ]

    def __str__(self):
        return f"Txn #{self.order_id} - {self.user.username} - ₹{self.amount} ({self.status})"

    def is_successful(self):
        return self.status == 'SUCCESS'

    def get_seat_ids_list(self):
        if not self.seat_ids:
            return []
        return [int(sid.strip()) for sid in self.seat_ids.split(',') if sid.strip().isdigit()]

    def get_seat_numbers_list(self):
        if not self.seat_numbers:
            return []
        return [s.strip() for s in self.seat_numbers.split(',') if s.strip()]

    def mark_success(self, payment_id, signature=None, payment_method=None):
        self.status = 'SUCCESS'
        self.payment_id = payment_id
        if signature:
            self.signature = signature
        if payment_method:
            self.payment_method = payment_method
        self.save()

    def mark_failed(self, error_code=None, error_description=None):
        self.status = 'FAILED'
        if error_code:
            self.error_code = error_code
        if error_description:
            self.error_description = error_description
        self.save()

    def mark_cancelled(self, reason='Cancelled by user'):
        self.status = 'CANCELLED'
        self.error_description = reason
        self.save()


class Booking(models.Model):
    STATUS_CHOICES = [
        ('CONFIRMED', 'Confirmed'),
        ('PAID', 'Paid'),
        ('PENDING', 'Pending'),
        ('CANCELLED', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    seat = models.OneToOneField(Seat, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    theater = models.ForeignKey(Theater, on_delete=models.CASCADE)
    transaction = models.ForeignKey(PaymentTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings', help_text="Payment transaction that confirmed this booking")
    booking_id = models.CharField(max_length=50, blank=True, db_index=True, help_text="Unique booking reference code (e.g. PMS-2026-XXXXX)")
    payment_reference = models.CharField(max_length=100, blank=True, help_text="Payment transaction reference ID")
    total_price = models.DecimalField(max_digits=8, decimal_places=2, default=200.00)
    payment_status = models.CharField(max_length=20, default='CONFIRMED', choices=STATUS_CHOICES, db_index=True)
    email_sent = models.BooleanField(default=False)
    booked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-booked_at']
        indexes = [
            models.Index(fields=['payment_status', 'booked_at'], name='booking_status_date_idx'),
            models.Index(fields=['theater', 'payment_status'], name='booking_thtr_status_idx'),
            models.Index(fields=['movie', 'payment_status'], name='booking_movie_status_idx'),
            models.Index(fields=['booked_at'], name='booking_booked_at_idx'),
            models.Index(fields=['user', 'booked_at'], name='booking_user_date_idx'),
        ]

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = generate_booking_id()
        if not self.payment_reference:
            self.payment_reference = generate_payment_reference()
        if not self.total_price or self.total_price <= 0:
            if self.theater and self.theater.price:
                self.total_price = self.theater.price
        super().save(*args, **kwargs)

    def get_seats_in_booking(self):
        """Returns QuerySet of all bookings sharing the same booking_id for multi-seat bookings"""
        return Booking.objects.filter(booking_id=self.booking_id)

    def get_seat_numbers(self):
        """Returns list of seat numbers in this booking group"""
        seats = list(self.get_seats_in_booking().values_list('seat__seat_number', flat=True))
        return seats if seats else [self.seat.seat_number]

    def get_total_amount(self):
        """Calculates total amount for all seats in this booking group"""
        group = self.get_seats_in_booking()
        if group.exists():
            return sum(b.total_price for b in group)
        return self.total_price

    def __str__(self):
        return f'Booking {self.booking_id} by {self.user.username} for {self.seat.seat_number} at {self.theater.name}'


class RecentlyViewed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='recent_views')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']

    def __str__(self):
        return f'{self.movie.name} viewed at {self.viewed_at}'


class HeroBanner(models.Model):
    """
    Hero carousel slide that can be managed from Django Admin.
    Upload an image, set title/subtitle/badge and it will appear
    on the homepage carousel automatically.
    """
    BADGE_COLOR_CHOICES = [
        ('danger',  'Red (Now Trending)'),
        ('warning', 'Yellow (Top Rated)'),
        ('info',    'Blue (Multi-City)'),
        ('success', 'Green (New Release)'),
        ('primary', 'Blue (Feature)'),
    ]

    title       = models.CharField(max_length=200, help_text="Main heading text shown on the slide")
    subtitle    = models.CharField(max_length=300, blank=True, default='', help_text="Short description under the title")
    badge       = models.CharField(max_length=80, blank=True, default='', help_text="Small badge label e.g. 'Now Trending'")
    badge_color = models.CharField(max_length=20, choices=BADGE_COLOR_CHOICES, default='danger')
    image       = models.ImageField(upload_to='banners/', help_text="Upload hero background image (recommended: 1240×300px or 16:9)")
    button_text = models.CharField(max_length=80, default='Explore Movies')
    button_url  = models.CharField(max_length=255, default='/movies/', help_text="URL the button links to")
    is_active   = models.BooleanField(default=True, help_text="Uncheck to hide this slide")
    order       = models.PositiveIntegerField(default=0, help_text="Lower number = shown first (0, 1, 2 ...)")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        verbose_name = 'Hero Banner Slide'
        verbose_name_plural = 'Hero Banner Slides'

    def __str__(self):
        return f'[{self.order}] {self.title} ({"Active" if self.is_active else "Hidden"})'


class CastMember(models.Model):
    ROLE_CHOICES = [
        ('Lead Actor', 'Lead Actor'),
        ('Lead Actress', 'Lead Actress'),
        ('Supporting Actor', 'Supporting Actor'),
        ('Supporting Actress', 'Supporting Actress'),
        ('Director', 'Director'),
        ('Music Director', 'Music Director'),
        ('Producer', 'Producer'),
        ('Writer', 'Writer'),
        ('Cinematographer', 'Cinematographer'),
    ]

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='cast_members')
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES, default='Lead Actor')
    character_name = models.CharField(max_length=200, blank=True, null=True, help_text="Character name (e.g. Neo, Cooper)")
    profile_image = models.ImageField(upload_to='cast/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (0=first)")

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        if self.character_name:
            return f"{self.name} as {self.character_name} ({self.role})"
        return f"{self.name} ({self.role})"


class MoviePoster(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='posters')
    image = models.ImageField(upload_to='movies/posters/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False, help_text="Mark as primary display poster")
    order = models.PositiveIntegerField(default=0, help_text="Display sequence")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', '-is_primary', 'created_at']

    def __str__(self):
        return f"Poster for {self.movie.name} (#{self.id})"


class Review(models.Model):
    RATING_CHOICES = [(i, f"{i}/10 Stars") for i in range(1, 11)]

    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='movie_reviews')
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews', help_text="Verified booking that unlocked this review")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, help_text="Rating on a 1-10 scale")
    headline = models.CharField(max_length=200, blank=True, help_text="Summary / title of your review")
    review_text = models.TextField(help_text="Detailed feedback and thoughts about the movie")
    is_verified_viewer = models.BooleanField(default=True, help_text="Indicates the reviewer booked and watched the movie")
    is_edited = models.BooleanField(default=False, help_text="True if review was edited after initial submission")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['movie', 'user'], name='unique_movie_user_review')
        ]

    def __str__(self):
        return f"{self.user.username}'s review for {self.movie.name} ({self.rating}/10)"

    def save(self, *args, **kwargs):
        if self.pk:
            self.is_edited = True
        super().save(*args, **kwargs)
        self.movie.update_average_rating()

    def delete(self, *args, **kwargs):
        movie = self.movie
        super().delete(*args, **kwargs)
        movie.update_average_rating()


class ReviewReport(models.Model):
    REASON_CHOICES = [
        ('SPAM', 'Spam, Advertising or Bots'),
        ('SPOILER', 'Contains Spoilers without warning'),
        ('OFFENSIVE', 'Offensive, Vulgar or Inappropriate Language'),
        ('HARASSMENT', 'Harassment, Hate Speech or Bullying'),
        ('FAKE', 'Fake or Irrelevant Content'),
        ('OTHER', 'Other Community Guideline Violation'),
    ]

    STATUS_CHOICES = [
        ('PENDING', 'Pending Moderation'),
        ('REVIEWED', 'Reviewed (Kept)'),
        ('ACTION_TAKEN', 'Action Taken (Review Removed)'),
        ('DISMISSED', 'Dismissed (Invalid Report)'),
    ]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_reports')
    reason = models.CharField(max_length=30, choices=REASON_CHOICES, default='OFFENSIVE')
    details = models.TextField(blank=True, null=True, help_text="Optional details explaining why this review was reported")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    admin_notes = models.TextField(blank=True, null=True, help_text="Internal notes by moderator")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['review', 'reported_by'], name='unique_review_user_report')
        ]

    def __str__(self):
        return f"Report #{self.id} on review #{self.review_id} by {self.reported_by.username} ({self.status})"