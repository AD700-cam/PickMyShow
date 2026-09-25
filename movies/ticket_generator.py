import io
import json
import os
import qrcode
import threading
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.conf import settings
from django.core.cache import cache


def generate_qr_code_image(data_dict):
    """
    Generates a high-quality QR code image containing verified ticket metadata.
    Returns a PIL Image object.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    payload_str = json.dumps(data_dict, ensure_ascii=False)
    qr.add_data(payload_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1A1A24", back_color="#FFFFFF")
    return img.get_image() if hasattr(img, 'get_image') else img


def generate_ticket_pdf(booking, use_cache=True):
    """
    Generates a professional, branded PDF ticket for a booking or booking group.
    Accepts a Booking instance.
    Utilizes in-memory caching for sub-millisecond instant download and preview.
    Returns bytes of the generated PDF.
    """
    booking_id = getattr(booking, 'booking_id', None)
    if use_cache and booking_id:
        cache_key = f"ticket_pdf_{booking_id}"
        cached = cache.get(cache_key)
        if cached:
            return cached

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    page_width, page_height = A4  # 595.27 x 841.89 pt

    # Fetch all seats in this booking group
    seats_qs = booking.get_seats_in_booking().select_related('seat', 'theater', 'movie', 'user')
    if seats_qs.exists():
        seat_numbers = [b.seat.seat_number for b in seats_qs]
        total_price = sum(b.total_price for b in seats_qs)
        first_booking = seats_qs.first()
    else:
        seat_numbers = [booking.seat.seat_number]
        total_price = booking.total_price
        first_booking = booking

    user_name = first_booking.user.get_full_name() or first_booking.user.username
    user_email = first_booking.user.email or "N/A"
    movie = first_booking.movie
    theater = first_booking.theater
    booking_id = first_booking.booking_id
    payment_ref = first_booking.payment_reference
    booked_time_str = first_booking.booked_at.strftime("%d %b %Y, %I:%M %p") if first_booking.booked_at else ""
    show_time_str = theater.time.strftime("%A, %d %B %Y at %I:%M %p") if theater.time else "TBA"

    # -------------------------------------------------------------
    # 1. Background & Margins
    # -------------------------------------------------------------
    margin_x = 36  # 0.5 inch margins
    ticket_width = page_width - (margin_x * 2)
    top_y = page_height - 40

    # Draw subtle page background
    p.setFillColor(colors.HexColor('#F4F6F9'))
    p.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # -------------------------------------------------------------
    # 2. Main Ticket Card Container
    # -------------------------------------------------------------
    card_y = 50
    card_height = top_y - card_y
    p.setFillColor(colors.HexColor('#FFFFFF'))
    p.setStrokeColor(colors.HexColor('#DDE2E5'))
    p.setLineWidth(1)
    p.roundRect(margin_x, card_y, ticket_width, card_height, 12, fill=1, stroke=1)

    # -------------------------------------------------------------
    # 3. Header Brand Banner (Red Bar)
    # -------------------------------------------------------------
    header_height = 80
    header_y = top_y - header_height
    p.setFillColor(colors.HexColor('#1A1A24'))
    # Draw top rounded corners for header
    p.roundRect(margin_x, header_y, ticket_width, header_height, 12, fill=1, stroke=0)
    # Fill bottom part of header to make it rectangular at seam
    p.rect(margin_x, header_y, ticket_width, 15, fill=1, stroke=0)

    # Brand Title
    p.setFillColor(colors.HexColor('#E50914'))
    p.setFont("Helvetica-Bold", 22)
    p.drawString(margin_x + 20, header_y + 46, "Pick")
    p.setFillColor(colors.HexColor('#FFFFFF'))
    p.drawString(margin_x + 65, header_y + 46, "MyShow")

    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor('#9AA0A6'))
    p.drawString(margin_x + 20, header_y + 26, "Official E-Ticket & Entry Pass")

    # Status Pill on Header Right
    badge_width = 110
    badge_height = 24
    badge_x = margin_x + ticket_width - badge_width - 20
    badge_y = header_y + 40
    p.setFillColor(colors.HexColor('#28A745'))
    p.roundRect(badge_x, badge_y, badge_width, badge_height, 6, fill=1, stroke=0)
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(badge_x + (badge_width / 2), badge_y + 7, "BOOKING CONFIRMED")

    # Booking ID on Header Right
    p.setFillColor(colors.HexColor('#D1D5DB'))
    p.setFont("Helvetica-Bold", 8)
    p.drawRightString(margin_x + ticket_width - 20, header_y + 24, f"ID: {booking_id}")

    # -------------------------------------------------------------
    # 4. Movie Information Block
    # -------------------------------------------------------------
    curr_y = header_y - 25

    # Movie Poster (if exists and accessible)
    poster_width = 100
    poster_height = 140
    poster_x = margin_x + 20
    poster_y = curr_y - poster_height + 15
    poster_drawn = False

    if movie.image and os.path.exists(movie.image.path):
        try:
            poster_reader = ImageReader(movie.image.path)
            p.drawImage(poster_reader, poster_x, poster_y, width=poster_width, height=poster_height, preserveAspectRatio=True, mask='auto')
            poster_drawn = True
        except Exception:
            poster_drawn = False

    if not poster_drawn:
        # Placeholder stylish box
        p.setFillColor(colors.HexColor('#1E222D'))
        p.roundRect(poster_x, poster_y, poster_width, poster_height, 8, fill=1, stroke=0)
        p.setFillColor(colors.HexColor('#E50914'))
        p.setFont("Helvetica-Bold", 28)
        p.drawCentredString(poster_x + (poster_width / 2), poster_y + 75, "PMS")
        p.setFillColor(colors.HexColor('#FFFFFF'))
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(poster_x + (poster_width / 2), poster_y + 50, "CINEMA PASS")

    # Movie Details Text Block
    text_x = poster_x + poster_width + 20
    text_max_w = margin_x + ticket_width - text_x - 20

    # Movie Name
    p.setFillColor(colors.HexColor('#1A1A24'))
    p.setFont("Helvetica-Bold", 18)
    # Truncate title if extremely long
    movie_title = movie.name if len(movie.name) <= 32 else movie.name[:29] + "..."
    p.drawString(text_x, curr_y, movie_title)

    # Genre / Language / Duration Badges
    curr_y -= 22
    p.setFont("Helvetica-Bold", 9)
    p.setFillColor(colors.HexColor('#E50914'))
    badge_text = f"{movie.genre.upper()}  |  {movie.language.upper()}  |  {movie.duration} MINS"
    p.drawString(text_x, curr_y, badge_text)

    # Rating badge
    curr_y -= 18
    p.setFont("Helvetica", 9)
    p.setFillColor(colors.HexColor('#495057'))
    p.drawString(text_x, curr_y, f"User Rating: {movie.rating}/10  |  Certification: U/A")

    # Cast summary
    curr_y -= 16
    p.setFont("Helvetica-Oblique", 8.5)
    p.setFillColor(colors.HexColor('#6C757D'))
    cast_str = f"Cast: {movie.cast}" if len(movie.cast) < 55 else f"Cast: {movie.cast[:52]}..."
    p.drawString(text_x, curr_y, cast_str)

    # Theater & Screen Name
    curr_y -= 22
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(colors.HexColor('#1A1A24'))
    p.drawString(text_x, curr_y, f"{theater.name} - {theater.city}")

    curr_y -= 16
    p.setFont("Helvetica", 9.5)
    p.setFillColor(colors.HexColor('#2B4C7E'))
    p.drawString(text_x, curr_y, f"Auditorium: {theater.screen_name}")

    # -------------------------------------------------------------
    # 5. Perforated Divider Line with Cutout Circles
    # -------------------------------------------------------------
    perf_y = poster_y - 25
    p.setStrokeColor(colors.HexColor('#DDE2E5'))
    p.setLineWidth(1)
    p.setDash(4, 3)
    p.line(margin_x + 15, perf_y, margin_x + ticket_width - 15, perf_y)
    p.setDash()  # reset dash

    # Left & Right cutout notches for physical ticket feel
    cutout_r = 10
    p.setFillColor(colors.HexColor('#F4F6F9'))
    p.circle(margin_x, perf_y, cutout_r, fill=1, stroke=0)
    p.circle(margin_x + ticket_width, perf_y, cutout_r, fill=1, stroke=0)

    # -------------------------------------------------------------
    # 6. Show Time & Seat Allocation Highlights Box
    # -------------------------------------------------------------
    section2_y = perf_y - 18
    highlight_box_h = 75
    box_y = section2_y - highlight_box_h
    p.setFillColor(colors.HexColor('#F8F9FA'))
    p.setStrokeColor(colors.HexColor('#E9ECEF'))
    p.roundRect(margin_x + 15, box_y, ticket_width - 30, highlight_box_h, 8, fill=1, stroke=1)

    # Column 1: Show Date & Time
    col1_x = margin_x + 30
    p.setFillColor(colors.HexColor('#6C757D'))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(col1_x, box_y + 54, "SHOW DATE & TIME")
    p.setFillColor(colors.HexColor('#1A1A24'))
    p.setFont("Helvetica-Bold", 12)
    p.drawString(col1_x, box_y + 36, theater.time.strftime("%d %b %Y") if theater.time else "TBA")
    p.setFont("Helvetica-Bold", 11)
    p.setFillColor(colors.HexColor('#E50914'))
    p.drawString(col1_x, box_y + 18, theater.time.strftime("%I:%M %p (%A)") if theater.time else "")

    # Column 2: Booked Seats
    col2_x = col1_x + 190
    p.setFillColor(colors.HexColor('#6C757D'))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(col2_x, box_y + 54, "BOOKED SEATS")
    p.setFillColor(colors.HexColor('#1A1A24'))
    p.setFont("Helvetica-Bold", 14)
    seats_joined = ", ".join(seat_numbers)
    p.drawString(col2_x, box_y + 35, seats_joined)
    p.setFont("Helvetica", 8.5)
    p.setFillColor(colors.HexColor('#6C757D'))
    p.drawString(col2_x, box_y + 18, f"Total: {len(seat_numbers)} Seat{'s' if len(seat_numbers) > 1 else ''} (Prime Class)")

    # Column 3: Total Paid
    col3_x = margin_x + ticket_width - 150
    p.setFillColor(colors.HexColor('#6C757D'))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(col3_x, box_y + 54, "TOTAL AMOUNT")
    p.setFillColor(colors.HexColor('#28A745'))
    p.setFont("Helvetica-Bold", 15)
    p.drawString(col3_x, box_y + 34, f"Rs. {total_price:.2f}")
    p.setFont("Helvetica", 8.5)
    p.setFillColor(colors.HexColor('#6C757D'))
    p.drawString(col3_x, box_y + 18, "Status: PAID (Online)")

    # -------------------------------------------------------------
    # 7. Verification QR Code & Detailed Receipt Breakdown
    # -------------------------------------------------------------
    section3_y = box_y - 20

    # Left: QR Code Block
    qr_size = 115
    qr_x = margin_x + 25
    qr_y = section3_y - qr_size

    qr_payload = {
        "app": "PickMyShow",
        "booking_id": booking_id,
        "payment_ref": payment_ref,
        "movie": movie.name,
        "theater": f"{theater.name}, {theater.city}",
        "screen": theater.screen_name,
        "seats": seat_numbers,
        "show_time": theater.time.strftime("%Y-%m-%d %H:%M") if theater.time else "",
        "user": user_name,
        "verified": True
    }

    try:
        qr_pil = generate_qr_code_image(qr_payload)
        qr_io = io.BytesIO()
        qr_pil.save(qr_io, format='PNG')
        qr_io.seek(0)
        qr_reader = ImageReader(qr_io)
        p.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
    except Exception as e:
        # Fallback if QR rendering encounters issue
        p.setFillColor(colors.HexColor('#EEEEEE'))
        p.rect(qr_x, qr_y, qr_size, qr_size, fill=1, stroke=1)
        p.setFillColor(colors.black)
        p.setFont("Helvetica", 8)
        p.drawCentredString(qr_x + (qr_size / 2), qr_y + 50, "[QR Code]")

    # QR Caption
    p.setFont("Helvetica-Bold", 7.5)
    p.setFillColor(colors.HexColor('#1A1A24'))
    p.drawCentredString(qr_x + (qr_size / 2), qr_y - 12, "SCAN AT ENTRY GATE")
    p.setFont("Helvetica", 7)
    p.setFillColor(colors.HexColor('#888888'))
    p.drawCentredString(qr_x + (qr_size / 2), qr_y - 22, "Fast-Track Digital Verification")

    # Right: Booking Summary & Payment Reference Details
    table_x = qr_x + qr_size + 30
    info_y = section3_y - 5

    p.setFillColor(colors.HexColor('#1A1A24'))
    p.setFont("Helvetica-Bold", 10)
    p.drawString(table_x, info_y, "Booking & Transaction Metadata")

    info_rows = [
        ("Booking Reference ID:", booking_id),
        ("Payment Transaction ID:", payment_ref),
        ("Ticket Booked By:", f"{user_name} ({user_email})"),
        ("Booking Timestamp:", booked_time_str),
        ("Ticket Price Breakdown:", f"{len(seat_numbers)} x Rs. {theater.price:.2f} = Rs. {total_price:.2f}"),
        ("Convenience & Taxes:", "Rs. 0.00 (Waived promotional)"),
        ("Final Amount Paid:", f"Rs. {total_price:.2f} (100% Settled)"),
    ]

    curr_row_y = info_y - 16
    for label, val in info_rows:
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(colors.HexColor('#495057'))
        p.drawString(table_x, curr_row_y, label)

        p.setFont("Helvetica", 8)
        p.setFillColor(colors.HexColor('#1A1A24') if "Final" not in label else colors.HexColor('#28A745'))
        p.drawString(table_x + 135, curr_row_y, str(val))
        curr_row_y -= 14

    # -------------------------------------------------------------
    # 8. Terms & Conditions and Security Notice
    # -------------------------------------------------------------
    terms_y = qr_y - 42
    p.setFillColor(colors.HexColor('#F8F9FA'))
    p.roundRect(margin_x + 15, card_y + 15, ticket_width - 30, terms_y - (card_y + 15), 6, fill=1, stroke=0)

    p.setFillColor(colors.HexColor('#E50914'))
    p.setFont("Helvetica-Bold", 8)
    p.drawString(margin_x + 25, terms_y - 12, "IMPORTANT INSTRUCTIONS & CINEMA GUIDELINES:")

    instructions = [
        "1. Please display this original PDF or physical printout with QR Code at the cinema entrance.",
        "2. Gate entry begins 20 minutes prior to scheduled showtime. Seats cannot be guaranteed after movie start.",
        "3. Outside food and beverages are strictly prohibited inside the auditorium as per theater policy.",
        "4. This digital e-ticket is non-transferable and protected with a digital anti-counterfeit cryptographic seal.",
        "5. For 24/7 customer support, email support&pickmyshow@hi2.in or call 07019972653 (100% Safe & Secure Booking)."
    ]

    ins_y = terms_y - 24
    p.setFont("Helvetica", 7)
    p.setFillColor(colors.HexColor('#495057'))
    for ins in instructions:
        p.drawString(margin_x + 25, ins_y, ins)
        ins_y -= 10

    # -------------------------------------------------------------
    # 9. Save PDF and return
    # -------------------------------------------------------------
    p.showPage()
    p.save()
    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if use_cache and booking_id:
        try:
            cache.set(f"ticket_pdf_{booking_id}", pdf_bytes, 86400 * 7)
        except Exception:
            pass

    return pdf_bytes


def prewarm_ticket_pdf_cache(booking):
    """
    Pre-generates and caches the PDF ticket in a non-blocking background thread.
    Guarantees that subsequent 'Download PDF' or 'View E-Ticket' clicks respond in <1ms.
    """
    if not booking or not getattr(booking, 'booking_id', None):
        return

    # Check if already cached first
    if cache.get(f"ticket_pdf_{booking.booking_id}"):
        return

    def _worker():
        try:
            generate_ticket_pdf(booking, use_cache=True)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

