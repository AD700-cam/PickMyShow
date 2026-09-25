import logging
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

from .models import Booking
from .ticket_generator import generate_ticket_pdf

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
)
def send_ticket_email_task(self, booking_id, recipient_email=None):
    """
    Asynchronous Celery background task that generates the PDF ticket
    and dispatches a confirmation email with the ticket attached.
    Automatically retries on failure with exponential backoff.
    """
    logger.info(f"[Celery] Starting ticket email dispatch for booking_id={booking_id} (Attempt: {self.request.retries + 1})")

    try:
        # Retrieve bookings in this transaction group
        bookings_qs = Booking.objects.filter(booking_id=booking_id).select_related('user', 'movie', 'theater', 'seat')
        if not bookings_qs.exists():
            logger.error(f"[Celery] No bookings found matching booking_id={booking_id}")
            return {"status": "error", "message": f"Booking {booking_id} not found"}

        first_booking = bookings_qs.first()
        target_email = recipient_email or first_booking.user.email
        if not target_email:
            logger.warning(f"[Celery] User {first_booking.user.username} has no email address configured.")
            return {"status": "skipped", "message": "No email address found for user"}

        # Gather details for email template
        seat_numbers = [b.seat.seat_number for b in bookings_qs]
        total_amount = sum(b.total_price for b in bookings_qs)
        user_name = first_booking.user.get_full_name() or first_booking.user.username
        movie = first_booking.movie
        theater = first_booking.theater

        context = {
            'user_name': user_name,
            'booking_id': first_booking.booking_id,
            'payment_reference': first_booking.payment_reference,
            'movie_name': movie.name,
            'genre': movie.genre,
            'language': movie.language,
            'duration': movie.duration,
            'theater_name': theater.name,
            'city': theater.city,
            'screen_name': theater.screen_name,
            'show_time': theater.time.strftime("%A, %d %B %Y at %I:%M %p") if theater.time else "TBA",
            'seat_numbers': ", ".join(seat_numbers),
            'total_amount': f"{total_amount:.2f}",
            'profile_url': "/profile/",
        }

        # Render HTML and plain text email content
        html_content = render_to_string('emails/ticket_confirmation.html', context)
        plain_content = strip_tags(html_content)

        subject = f"Your Movie Ticket: {movie.name} - {first_booking.booking_id} (PickMyShow)"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'PickMyShow <support&pickmyshow@hi2.in>')

        # Generate PDF Ticket
        pdf_bytes = generate_ticket_pdf(first_booking)
        filename = f"PickMyShow_Ticket_{first_booking.booking_id}.pdf"

        # Build Email Message
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_content,
            from_email=from_email,
            to=[target_email],
        )
        email.attach_alternative(html_content, "text/html")
        email.attach(filename, pdf_bytes, "application/pdf")

        # Send Email
        email.send(fail_silently=False)

        # Mark bookings as emailed
        bookings_qs.update(email_sent=True)

        logger.info(f"[Celery] Ticket email successfully sent to {target_email} for booking_id={booking_id}")
        return {
            "status": "success",
            "booking_id": booking_id,
            "recipient": target_email,
            "seats": seat_numbers,
        }

    except Exception as exc:
        logger.error(f"[Celery] Error delivering ticket email for booking_id={booking_id}: {exc}")
        # Re-raise so Celery autoretry triggers according to policy
        raise exc
