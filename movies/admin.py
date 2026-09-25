from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    Movie, Genre, Language, CastMember, MoviePoster,
    Theater, Seat, Booking, RecentlyViewed, HeroBanner,
    Review, ReviewReport, PaymentTransaction
)


class MoviePosterInline(admin.TabularInline):
    model = MoviePoster
    extra = 1
    fields = ['poster_thumb', 'image', 'caption', 'is_primary', 'order']
    readonly_fields = ['poster_thumb']

    def poster_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:50px;height:70px;object-fit:cover;border-radius:4px;" />',
                obj.image.url
            )
        return 'No Image'
    poster_thumb.short_description = 'Preview'


class CastMemberInline(admin.TabularInline):
    model = CastMember
    extra = 1
    fields = ['photo_thumb', 'name', 'role', 'character_name', 'profile_image', 'order']
    readonly_fields = ['photo_thumb']

    def photo_thumb(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width:40px;height:40px;object-fit:cover;border-radius:50%;" />',
                obj.profile_image.url
            )
        return format_html('<span style="color:#aaa;">No photo</span>')
    photo_thumb.short_description = 'Photo'


class TheaterInline(admin.TabularInline):
    model = Theater
    extra = 0
    fields = ['name', 'city', 'screen_name', 'theater_chain', 'time', 'price']
    show_change_link = True
    verbose_name = 'Show Schedule'
    verbose_name_plural = 'Scheduled Shows Across Theaters'


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ['user', 'rating', 'headline', 'is_verified_viewer', 'is_edited', 'created_at']
    fields = ['user', 'rating', 'headline', 'is_verified_viewer', 'is_edited', 'created_at']
    can_delete = True
    show_change_link = True


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = [
        'poster_thumbnail', 'name', 'age_certification_badge',
        'genre', 'language', 'rating', 'reviews_count_display',
        'duration_display', 'release_date', 'trailer_status'
    ]
    list_display_links = ['poster_thumbnail', 'name']
    list_filter = ['age_certification', 'genre', 'language', 'release_date']
    search_fields = ['name', 'cast', 'director', 'description', 'synopsis']
    list_per_page = 20
    readonly_fields = ['poster_preview', 'trailer_preview', 'rating']
    filter_horizontal = ['genres', 'languages']
    inlines = [MoviePosterInline, CastMemberInline, TheaterInline, ReviewInline]

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'age_certification', 'genre', 'genres',
                'language', 'languages', 'rating', 'duration',
                'release_date', 'views_count'
            )
        }),
        ('Posters & Media Assets', {
            'fields': ('image', 'poster_preview', 'trailer_url', 'trailer_preview'),
            'description': 'Main poster and YouTube trailer embed link.'
        }),
        ('Synopsis, Crew & Cast', {
            'fields': ('director', 'cast', 'description', 'synopsis'),
            'description': 'Full story overview and crew credits.'
        }),
    )

    def poster_thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:45px;height:65px;object-fit:cover;border-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return format_html('<span style="color:#aaa;font-size:11px;">No Image</span>')
    poster_thumbnail.short_description = 'Poster'

    def poster_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:200px;max-height:300px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return 'No image uploaded yet.'
    poster_preview.short_description = 'Current Poster'

    def age_certification_badge(self, obj):
        colors = {
            'U': '#28a745',
            'UA 7+': '#17a2b8',
            'UA 13+': '#ffc107',
            'UA 16+': '#fd7e14',
            'A': '#dc3545',
            'PG-13': '#6f42c1',
            'R': '#e83e8c',
        }
        bg = colors.get(obj.age_certification, '#6c757d')
        color = '#000' if obj.age_certification in ['UA 13+', 'U'] else '#fff'
        return format_html(
            '<span style="background:{};color:{};font-weight:700;padding:2px 8px;border-radius:12px;font-size:11px;">{}</span>',
            bg, color, obj.age_certification
        )
    age_certification_badge.short_description = 'Age Cert.'

    def trailer_status(self, obj):
        embed_url = obj.get_youtube_embed_url()
        if embed_url:
            return format_html(
                '<a href="{}" target="_blank" style="color:#e50914;font-weight:600;"><i class="fas fa-play-circle mr-1"></i>Watch</a>',
                obj.trailer_url
            )
        return format_html('<span style="color:#999;font-size:11px;">No Trailer</span>')
    trailer_status.short_description = 'Trailer'

    def trailer_preview(self, obj):
        embed_url = obj.get_youtube_embed_url()
        if embed_url:
            return format_html(
                '<div style="max-width:560px;">'
                '<iframe width="100%" height="315" src="{}" title="YouTube video player" '
                'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                'allowfullscreen style="border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.25);"></iframe>'
                '<p style="color:#666;font-size:12px;margin-top:4px;">Secure privacy-enhanced embed via youtube-nocookie.com</p>'
                '</div>',
                embed_url
            )
        return format_html('<span style="color:#888;">Enter a valid YouTube URL (e.g. https://www.youtube.com/watch?v=...) to see live trailer preview.</span>')
    trailer_preview.short_description = 'Live Trailer Preview'

    def duration_display(self, obj):
        hours = obj.duration // 60
        mins = obj.duration % 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    duration_display.short_description = 'Duration'

    def reviews_count_display(self, obj):
        count = obj.reviews.count()
        return format_html('<b>{}</b> reviews', count)
    reviews_count_display.short_description = 'Reviews'


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon_preview', 'movies_count']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

    def icon_preview(self, obj):
        return format_html('<i class="fas {} mr-1"></i> {}', obj.icon, obj.icon)
    icon_preview.short_description = 'Icon'

    def movies_count(self, obj):
        return obj.movies.count()
    movies_count.short_description = 'Assigned Movies'


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'movies_count']
    search_fields = ['name', 'code']

    def movies_count(self, obj):
        return obj.movies.count()
    movies_count.short_description = 'Assigned Movies'


@admin.register(CastMember)
class CastMemberAdmin(admin.ModelAdmin):
    list_display = ['photo_thumbnail', 'name', 'movie', 'role', 'character_name', 'order']
    list_filter = ['role', 'movie']
    search_fields = ['name', 'character_name', 'movie__name']
    list_editable = ['order', 'role']
    list_per_page = 30

    def photo_thumbnail(self, obj):
        if obj.profile_image:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;object-fit:cover;border-radius:50%;" />',
                obj.profile_image.url
            )
        return format_html('<span style="color:#aaa;font-size:11px;">No photo</span>')
    photo_thumbnail.short_description = 'Photo'


@admin.register(MoviePoster)
class MoviePosterAdmin(admin.ModelAdmin):
    list_display = ['poster_thumb', 'movie', 'caption', 'is_primary', 'order', 'created_at']
    list_filter = ['is_primary', 'movie']
    list_editable = ['is_primary', 'order']
    search_fields = ['caption', 'movie__name']

    def poster_thumb(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:45px;height:65px;object-fit:cover;border-radius:4px;" />',
                obj.image.url
            )
        return 'No Image'
    poster_thumb.short_description = 'Preview'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['movie', 'user', 'rating_stars', 'headline', 'verified_badge', 'is_edited', 'created_at']
    list_filter = ['rating', 'is_verified_viewer', 'is_edited', 'created_at', 'movie']
    search_fields = ['movie__name', 'user__username', 'headline', 'review_text']
    readonly_fields = ['created_at', 'updated_at']
    actions = ['recalculate_ratings', 'mark_as_verified']

    def rating_stars(self, obj):
        return format_html(
            '<span style="color:#f5c518;font-weight:700;">★ {}</span> / 10',
            obj.rating
        )
    rating_stars.short_description = 'Rating'

    def verified_badge(self, obj):
        if obj.is_verified_viewer:
            return format_html(
                '<span style="background:#28a745;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">'
                '<i class="fas fa-check-circle mr-1"></i>Verified Viewer</span>'
            )
        return format_html('<span style="color:#aaa;font-size:11px;">Standard</span>')
    verified_badge.short_description = 'Verified'

    @admin.action(description="Recalculate average ratings for selected movies")
    def recalculate_ratings(self, request, queryset):
        movies = {r.movie for r in queryset}
        for m in movies:
            m.update_average_rating()
        self.message_user(request, f"Updated average rating for {len(movies)} movie(s).")

    @admin.action(description="Mark selected reviews as Verified Viewer")
    def mark_as_verified(self, request, queryset):
        queryset.update(is_verified_viewer=True)
        self.message_user(request, f"Marked {queryset.count()} reviews as Verified Viewer.")


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'review_summary', 'reported_by', 'reason_badge', 'status_badge', 'created_at']
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['review__movie__name', 'review__headline', 'reported_by__username', 'details']
    readonly_fields = ['created_at']
    actions = ['dismiss_reports', 'take_action_remove_review']

    def review_summary(self, obj):
        return format_html(
            '<b>{}</b>: "{}" (by {})',
            obj.review.movie.name,
            (obj.review.headline or obj.review.review_text)[:40],
            obj.review.user.username
        )
    review_summary.short_description = 'Target Review'

    def reason_badge(self, obj):
        return format_html(
            '<span style="background:#6c757d;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;">{}</span>',
            obj.get_reason_display()
        )
    reason_badge.short_description = 'Reason'

    def status_badge(self, obj):
        colors = {
            'PENDING': '#dc3545',
            'REVIEWED': '#17a2b8',
            'ACTION_TAKEN': '#ffc107',
            'DISMISSED': '#6c757d',
        }
        bg = colors.get(obj.status, '#6c757d')
        color = '#000' if obj.status == 'ACTION_TAKEN' else '#fff'
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;font-weight:600;font-size:11px;">{}</span>',
            bg, color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    @admin.action(description="Dismiss selected reports (Mark as invalid)")
    def dismiss_reports(self, request, queryset):
        queryset.update(status='DISMISSED')
        self.message_user(request, f"Dismissed {queryset.count()} reports.")

    @admin.action(description="Action Taken: Delete reported reviews and resolve reports")
    def take_action_remove_review(self, request, queryset):
        reviews_to_delete = [report.review for report in queryset]
        count = len(reviews_to_delete)
        for r in reviews_to_delete:
            r.delete()
        queryset.update(status='ACTION_TAKEN')
        self.message_user(request, f"Removed {count} reported review(s) and marked reports as Action Taken.")


@admin.register(Theater)
class TheaterAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'screen_name', 'theater_chain', 'price', 'movie', 'time', 'seats_status']
    list_filter = ['city', 'theater_chain', 'movie', 'time']
    search_fields = ['name', 'city', 'screen_name', 'movie__name']
    list_per_page = 30

    def seats_status(self, obj):
        total = obj.seats.count()
        booked = obj.seats.filter(is_booked=True).count()
        return format_html('<b>{}/{}</b> booked', booked, total)
    seats_status.short_description = 'Seat Occupancy'


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['theater', 'seat_number', 'status_badge', 'is_booked', 'reserved_by', 'reserved_until', 'remaining_seconds_display']
    list_filter  = ['is_booked', 'theater__city', 'theater']
    search_fields = ['seat_number', 'theater__name', 'reserved_by__username']
    readonly_fields = ['reserved_until', 'reserved_by']

    def status_badge(self, obj):
        status = obj.get_status()
        if status == 'booked':
            return format_html('<span style="background:#dc3545;color:#fff;padding:2px 8px;border-radius:10px;font-weight:700;font-size:11px;">Booked</span>')
        elif status in ['reserved', 'reserved_by_you']:
            rem = obj.get_remaining_seconds()
            return format_html('<span style="background:#ffc107;color:#000;padding:2px 8px;border-radius:10px;font-weight:700;font-size:11px;">Reserved ({}s)</span>', rem)
        return format_html('<span style="background:#28a745;color:#fff;padding:2px 8px;border-radius:10px;font-weight:700;font-size:11px;">Available</span>')
    status_badge.short_description = 'Live Status'

    def remaining_seconds_display(self, obj):
        rem = obj.get_remaining_seconds()
        return f"{rem}s" if rem > 0 else "-"
    remaining_seconds_display.short_description = 'Hold Remaining'



@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'payment_id', 'user', 'movie',
        'amount_display', 'status_badge', 'payment_method',
        'seat_numbers', 'created_at'
    ]
    list_filter = ['status', 'gateway', 'payment_method', 'created_at']
    search_fields = ['order_id', 'payment_id', 'booking_id', 'user__username', 'user__email', 'movie__name']
    readonly_fields = ['created_at', 'updated_at', 'signature']
    list_per_page = 25

    def amount_display(self, obj):
        return format_html('<b>₹{}</b>', obj.amount)
    amount_display.short_description = 'Amount (₹)'

    def status_badge(self, obj):
        colors = {
            'SUCCESS': '#28a745',
            'PENDING': '#ffc107',
            'INITIATED': '#17a2b8',
            'FAILED': '#dc3545',
            'CANCELLED': '#6c757d',
            'REFUNDED': '#fd7e14',
        }
        bg = colors.get(obj.status, '#6c757d')
        color = '#000' if obj.status in ['PENDING', 'INITIATED'] else '#fff'
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;border-radius:12px;font-weight:700;font-size:11px;">{}</span>',
            bg, color, obj.get_status_display()
        )
    status_badge.short_description = 'Payment Status'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ['booking_id', 'user', 'seat', 'movie', 'theater', 'total_price', 'payment_status', 'transaction', 'email_sent', 'booked_at']
    list_filter   = ['payment_status', 'email_sent', 'booked_at', 'theater__city']
    search_fields = ['booking_id', 'payment_reference', 'user__username', 'user__email', 'movie__name', 'theater__name']
    readonly_fields = ['booked_at', 'transaction']


@admin.register(RecentlyViewed)
class RecentlyViewedAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_key', 'movie', 'viewed_at']
    list_filter  = ['viewed_at']


@admin.register(HeroBanner)
class HeroBannerAdmin(admin.ModelAdmin):
    list_display  = ['slide_preview', 'order', 'title', 'badge', 'badge_color', 'is_active']
    list_display_links = ['slide_preview', 'title']
    list_editable = ['order', 'is_active']
    list_filter   = ['is_active', 'badge_color']
    readonly_fields = ['banner_preview']
    ordering      = ['order']

    fieldsets = (
        ('Slide Content', {
            'fields': ('title', 'subtitle', 'badge', 'badge_color'),
            'description': 'Text shown on top of the hero image.'
        }),
        ('Hero Image', {
            'fields': ('image', 'banner_preview'),
            'description': 'Upload background image. Recommended: 1240x300px (wide landscape).'
        }),
        ('Button & Link', {
            'fields': ('button_text', 'button_url'),
        }),
        ('Visibility', {
            'fields': ('order', 'is_active'),
            'description': 'Order 0 = first slide. Uncheck is_active to hide without deleting.'
        }),
    )

    def slide_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:120px;height:45px;object-fit:cover;border-radius:4px;box-shadow:0 2px 6px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return format_html('<span style="color:#aaa;font-size:11px;">No Image</span>')
    slide_preview.short_description = 'Preview'

    def banner_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-width:500px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.2);" />',
                obj.image.url
            )
        return 'No image uploaded yet.'
    banner_preview.short_description = 'Current Banner Preview'


# Customize admin site branding
admin.site.site_header  = '🎬 PickMyShow Admin'
admin.site.site_title   = 'PickMyShow'
admin.site.index_title  = 'Welcome to PickMyShow Control Panel'
