import os
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from movies.models import Movie, Theater, Seat, Booking, RecentlyViewed, HeroBanner


def generate_banner_image(filepath, title, subtitle, badge, color1, color2):
    """Generate a cinematic-wide hero banner (1440x480) for the BMS-style homepage carousel."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    w, h = 1440, 480

    # ── Fast 2D diagonal gradient using Pillow Bilinear Resizing ───────────────
    resample_filter = getattr(getattr(Image, 'Resampling', Image), 'BILINEAR', Image.BILINEAR)
    base = Image.new('RGB', (2, 2))
    mid_color = tuple(int((c1 + c2) / 2) for c1, c2 in zip(color1, color2))
    base.putpixel((0, 0), color1)
    base.putpixel((1, 0), mid_color)
    base.putpixel((0, 1), mid_color)
    base.putpixel((1, 1), color2)
    img = base.resize((w, h), resample=resample_filter)
    draw = ImageDraw.Draw(img)

    # Large decorative concentric arcs — right half gives visual depth
    for rad in range(60, 350, 45):
        draw.arc(
            [w - 400 - rad, h // 2 - rad, w - 400 + rad, h // 2 + rad],
            start=0, end=360,
            fill=(255, 255, 255),
            width=1,
        )

    # Faint film-strip notches along bottom edge
    for fx in range(0, w, 60):
        draw.rectangle([fx + 8, h - 22, fx + 42, h - 8],
                       fill=(0, 0, 0), outline=(255, 255, 255), width=1)

    # Red top accent bar (matches the CSS ::before strip)
    draw.rectangle([0, 0, w, 5], fill=(229, 9, 20))

    # ─── Left-panel overlay: fast RGBA composite ─────────────────────────────
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    # Solid dark band on left 420px, then fade-out gradient
    ov_draw.rectangle([0, 0, 420, h], fill=(0, 0, 0, 155))
    for gx in range(421, 680):
        alpha_val = int(155 * (1 - (gx - 420) / 260))
        ov_draw.line([(gx, 0), (gx, h)], fill=(0, 0, 0, alpha_val))
    img_rgba = img.convert('RGBA')
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert('RGB')
    draw = ImageDraw.Draw(img)


    # Badge pill
    badge_text = badge.upper()
    bw = len(badge_text) * 11 + 28
    draw.rounded_rectangle([48, 48, 48 + bw, 82], radius=6, fill=(229, 9, 20))
    draw.text((48 + bw // 2, 65), badge_text, fill=(255, 255, 255), anchor='mm')

    # Title  (large)
    draw.text((48, 110), title, fill=(255, 255, 255), anchor='lm')

    # Subtitle
    draw.text((48, 165), subtitle, fill=(200, 215, 235), anchor='lm')

    # Horizontal rule
    draw.rectangle([48, 190, 340, 192], fill=(229, 9, 20))

    # CTA button mockup
    draw.rounded_rectangle([48, 210, 260, 258], radius=8, fill=(229, 9, 20))
    draw.text((154, 234), '▶  Book Now', fill=(255, 255, 255), anchor='mm')

    # PickMyShow watermark — lower-right
    draw.text((w - 40, h - 22), 'PickMyShow', fill=(255, 255, 255), anchor='rm')

    img.save(filepath, 'JPEG', quality=92)



def generate_movie_poster(filepath, title, subtitle, genre, lang, rating, color1, color2):
    if os.path.exists(filepath):
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    w, h = 600, 900
    resample_filter = getattr(getattr(Image, 'Resampling', Image), 'BILINEAR', Image.BILINEAR)
    base = Image.new('RGB', (1, 2))
    base.putpixel((0, 0), color1)
    base.putpixel((0, 1), color2)
    img = base.resize((w, h), resample=resample_filter)
    draw = ImageDraw.Draw(img)

    # Decorative background circles & arches
    for rad in range(70, 280, 35):
        draw.arc([w//2 - rad, 220 - rad, w//2 + rad, 220 + rad], 0, 360, fill=(255, 255, 255, 25), width=2)

    # Outer border
    draw.rectangle([20, 20, w-20, h-20], outline=(255, 255, 255, 140), width=3)
    draw.rectangle([26, 26, w-26, h-26], outline=(255, 215, 0, 100), width=1)

    # Header badge
    draw.rectangle([w//2 - 130, 45, w//2 + 130, 75], fill=(229, 9, 20))
    draw.text((w//2, 60), 'PICKMYSHOW EXCLUSIVE', fill=(255, 255, 255), anchor='mm')

    # Star rating badge
    draw.rectangle([w//2 - 70, 380, w//2 + 70, 415], fill=(0, 0, 0, 220), outline=(255, 193, 7), width=2)
    draw.text((w//2, 397), f'★ {rating} / 10', fill=(255, 193, 7), anchor='mm')

    # Title area
    draw.text((w//2, 470), title.upper(), fill=(255, 255, 255), anchor='mm')
    draw.text((w//2, 510), subtitle, fill=(230, 230, 230), anchor='mm')

    # Meta banner
    draw.rectangle([40, 560, w-40, 600], fill=(255, 255, 255, 30))
    draw.text((w//2, 580), f'{genre.upper()}  •  {lang.upper()}', fill=(255, 215, 0), anchor='mm')

    # Tagline / cinema banner
    draw.rectangle([60, 680, w-60, 720], fill=(0, 0, 0, 180))
    draw.text((w//2, 700), 'EXPERIENCE IN IMAX 3D & 4DX', fill=(200, 225, 255), anchor='mm')

    # Footer
    draw.text((w//2, 845), 'IN CINEMAS WORLDWIDE', fill=(210, 210, 210), anchor='mm')

    img.save(filepath, 'JPEG', quality=95)


class Command(BaseCommand):
    help = 'Seeds database with 16 realistic copyright-free movies, posters, 5 Indian users, and theater bookings'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Seeding 16 movies and 5 Indian user profiles for PickMyShow...'))

        # 1. CREATE 5 INDIAN USERS
        indian_users_data = [
            ('aarav_sharma', 'Aarav', 'Sharma', 'aarav.sharma@example.com', 'password123'),
            ('priya_patel', 'Priya', 'Patel', 'priya.patel@example.com', 'password123'),
            ('rohit_verma', 'Rohit', 'Verma', 'rohit.verma@example.com', 'password123'),
            ('ananya_iyer', 'Ananya', 'Iyer', 'ananya.iyer@example.com', 'password123'),
            ('vikram_singh', 'Vikram', 'Singh', 'vikram.singh@example.com', 'password123'),
        ]

        created_users = {}
        for username, fname, lname, email, pwd in indian_users_data:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': fname, 'last_name': lname, 'email': email}
            )
            user.set_password(pwd)
            user.save()
            created_users[username] = user

        # Also maintain admin and demo user
        admin_user, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@pickmyshow.com', 'is_staff': True, 'is_superuser': True}
        )
        admin_user.set_password('admin123')
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        # 2. 16 MOVIES WITH DISTINCT GENRES, LANGUAGES, RATINGS & POSTERS
        movies_dataset = [
            {
                'name': 'Kalki 2898 AD',
                'subtitle': 'A Modern Sci-Fi Epoch',
                'genre': 'Sci-Fi',
                'language': 'Telugu',
                'rating': Decimal('8.8'),
                'release_date': datetime.date(2024, 6, 27),
                'duration': 181,
                'views_count': 3450,
                'cast': 'Prabhas, Amitabh Bachchan, Kamal Haasan, Deepika Padukone',
                'description': 'Set in a post-apocalyptic future, a chosen warrior embarks on a mythological journey to protect humanity against dystopian forces in Kasi.',
                'color1': (15, 23, 42),
                'color2': (88, 28, 135),
                'img_filename': 'kalki_2898_ad.jpg'
            },
            {
                'name': 'Jawan',
                'subtitle': 'The Ultimate Vigilante Thriller',
                'genre': 'Action',
                'language': 'Hindi',
                'rating': Decimal('8.4'),
                'release_date': datetime.date(2023, 9, 7),
                'duration': 169,
                'views_count': 3100,
                'cast': 'Shah Rukh Khan, Nayanthara, Vijay Sethupathi, Deepika Padukone',
                'description': 'A high-octane emotional action thriller of a man driven by personal vendetta to right the societal wrongs and fulfill a promise made years ago.',
                'color1': (127, 29, 29),
                'color2': (17, 24, 39),
                'img_filename': 'jawan.jpg'
            },
            {
                'name': 'Interstellar Odyssey',
                'subtitle': 'Beyond Space and Time',
                'genre': 'Sci-Fi',
                'language': 'English',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2024, 1, 15),
                'duration': 169,
                'views_count': 2890,
                'cast': 'Matthew McConaughey, Anne Hathaway, Jessica Chastain, Michael Caine',
                'description': 'When Earth becomes uninhabitable, a former NASA pilot leads an intrepid team through a mysterious wormhole across galaxies to find humanity a new home.',
                'color1': (10, 15, 30),
                'color2': (30, 58, 138),
                'img_filename': 'interstellar_odyssey.jpg'
            },
            {
                'name': 'Brahmastra: Part One - Shiva',
                'subtitle': 'The Legend of the Astras',
                'genre': 'Fantasy',
                'language': 'Hindi',
                'rating': Decimal('8.1'),
                'release_date': datetime.date(2023, 9, 9),
                'duration': 167,
                'views_count': 2200,
                'cast': 'Ranbir Kapoor, Alia Bhatt, Amitabh Bachchan, Nagarjuna Akkineni',
                'description': 'Shiva discovers his divine connection to the elemental power of fire, unlocking ancient secrets that guard the supreme weapon of the gods.',
                'color1': (180, 83, 9),
                'color2': (69, 10, 10),
                'img_filename': 'brahmastra.jpg'
            },
            {
                'name': 'Leo: Bloody Sweet',
                'subtitle': 'Past Never Dies',
                'genre': 'Action',
                'language': 'Tamil',
                'rating': Decimal('8.0'),
                'release_date': datetime.date(2023, 10, 19),
                'duration': 164,
                'views_count': 2600,
                'cast': 'Thalapathy Vijay, Sanjay Dutt, Trisha Krishnan, Arjun Sarja',
                'description': 'A calm family man running a cafe in Kashmir is hunted by notorious mobsters who insist he is their long-lost feared enforcer Leo Das.',
                'color1': (153, 27, 27),
                'color2': (31, 41, 55),
                'img_filename': 'leo_bloody_sweet.jpg'
            },
            {
                'name': 'Manjummel Boys',
                'subtitle': 'Bond of Brotherhood',
                'genre': 'Thriller',
                'language': 'Malayalam',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2024, 2, 22),
                'duration': 135,
                'views_count': 2450,
                'cast': 'Soubin Shahir, Sreenath Bhasi, Balu Varghese, Ganapathi',
                'description': 'A tight-knit group of friends from a small town face an impossible rescue mission in the treacherous depths of the forbidden Guna Caves.',
                'color1': (6, 78, 59),
                'color2': (15, 23, 42),
                'img_filename': 'manjummel_boys.jpg'
            },
            {
                'name': 'Laapataa Ladies',
                'subtitle': 'A Tale of Two Brides',
                'genre': 'Comedy',
                'language': 'Hindi',
                'rating': Decimal('8.7'),
                'release_date': datetime.date(2024, 3, 1),
                'duration': 122,
                'views_count': 1950,
                'cast': 'Nitanshi Goel, Pratibha Ranta, Sparsh Shrivastava, Ravi Kishan',
                'description': 'A delightful comedy of errors unfolds in rural India when two young brides with veiled faces are accidentally swapped on a crowded train.',
                'color1': (202, 138, 4),
                'color2': (120, 53, 15),
                'img_filename': 'laapataa_ladies.jpg'
            },
            {
                'name': 'Stree 2: Sarkate Ka Aatank',
                'subtitle': 'The Terror of the Headless',
                'genre': 'Horror',
                'language': 'Hindi',
                'rating': Decimal('8.3'),
                'release_date': datetime.date(2024, 8, 15),
                'duration': 147,
                'views_count': 3300,
                'cast': 'Rajkummar Rao, Shraddha Kapoor, Pankaj Tripathi, Abhishek Banerjee',
                'description': 'The beloved quirky town of Chanderi faces a sinister new entity named Sarkata, uniting the gang with the supernatural protector Stree.',
                'color1': (88, 28, 135),
                'color2': (17, 24, 39),
                'img_filename': 'stree_2.jpg'
            },
            {
                'name': 'Kantara: A Legend',
                'subtitle': 'Divine Folklore and Valor',
                'genre': 'Drama',
                'language': 'Kannada',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2023, 9, 30),
                'duration': 150,
                'views_count': 2800,
                'cast': 'Rishab Shetty, Sapthami Gowda, Kishore, Achyuth Kumar',
                'description': 'In a coastal hamlet, a rebellion of nature and ancestral spirits erupts as a brave tribal youth confronts ruthless forest encroachment.',
                'color1': (180, 83, 9),
                'color2': (20, 83, 45),
                'img_filename': 'kantara.jpg'
            },
            {
                'name': 'Pushpa 2: The Rule',
                'subtitle': 'The Empire of Red Sandalwood',
                'genre': 'Action',
                'language': 'Telugu',
                'rating': Decimal('8.6'),
                'release_date': datetime.date(2024, 12, 5),
                'duration': 175,
                'views_count': 3900,
                'cast': 'Allu Arjun, Rashmika Mandanna, Fahadh Faasil, Jagapathi Babu',
                'description': 'Pushpa Raj cements his reign over the red sandalwood empire while fighting fierce international syndicates and relentless police enforcement.',
                'color1': (185, 28, 28),
                'color2': (67, 20, 7),
                'img_filename': 'pushpa_2.jpg'
            },
            {
                'name': 'The Dark Knight of Gotham',
                'subtitle': 'Guardian of the Night',
                'genre': 'Action',
                'language': 'English',
                'rating': Decimal('9.0'),
                'release_date': datetime.date(2023, 8, 20),
                'duration': 152,
                'views_count': 3100,
                'cast': 'Christian Bale, Heath Ledger, Aaron Eckhart, Gary Oldman',
                'description': 'Batman faces his ultimate psychological and ideological nemesis in the form of the chaotic Joker who threatens to dismantle Gotham society.',
                'color1': (15, 23, 42),
                'color2': (2, 6, 23),
                'img_filename': 'dark_knight.jpg'
            },
            {
                'name': 'Oppenheimer: The Atomic Dawn',
                'subtitle': 'The Man Who Shook The World',
                'genre': 'Drama',
                'language': 'English',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2023, 7, 21),
                'duration': 180,
                'views_count': 2750,
                'cast': 'Cillian Murphy, Emily Blunt, Matt Damon, Robert Downey Jr.',
                'description': 'The riveting historical chronicle of J. Robert Oppenheimer leading the top-secret Manhattan Project to create the first atomic weapon.',
                'color1': (217, 119, 6),
                'color2': (24, 24, 27),
                'img_filename': 'oppenheimer.jpg'
            },
            {
                'name': 'Spider-Verse: Multiverse Chaos',
                'subtitle': 'Across Dimensions',
                'genre': 'Animation',
                'language': 'English',
                'rating': Decimal('8.7'),
                'release_date': datetime.date(2023, 6, 2),
                'duration': 140,
                'views_count': 2600,
                'cast': 'Shameik Moore, Hailee Steinfeld, Oscar Isaac, Daniel Kaluuya',
                'description': 'Miles Morales journeys across dynamic animated dimensions, teaming up with Spider-Heroes to redefine what it truly means to be a hero.',
                'color1': (190, 18, 60),
                'color2': (30, 58, 138),
                'img_filename': 'spider_verse.jpg'
            },
            {
                'name': 'Sita Ramam: A Love Story',
                'subtitle': 'Love Through The Battlefield',
                'genre': 'Romance',
                'language': 'Telugu',
                'rating': Decimal('8.5'),
                'release_date': datetime.date(2023, 8, 5),
                'duration': 163,
                'views_count': 1850,
                'cast': 'Dulquer Salmaan, Mrunal Thakur, Rashmika Mandanna, Sumanth',
                'description': 'An orphaned army lieutenant serving at the Kashmir border receives heartfelt letters from an enigmatic woman named Sita, sparking an timeless romance.',
                'color1': (190, 24, 93),
                'color2': (67, 56, 202),
                'img_filename': 'sita_ramam.jpg'
            },
            {
                'name': 'Drishyam 2: The Resumption',
                'subtitle': 'Guilt, Secrets & Family',
                'genre': 'Thriller',
                'language': 'Hindi',
                'rating': Decimal('8.6'),
                'release_date': datetime.date(2023, 11, 18),
                'duration': 140,
                'views_count': 2400,
                'cast': 'Ajay Devgn, Tabu, Akshaye Khanna, Shriya Saran',
                'description': 'Seven years after the original case, a shrewd police officer reopens the investigation, forcing Vijay Salgaonkar to execute his master plan once again.',
                'color1': (24, 24, 27),
                'color2': (3, 105, 161),
                'img_filename': 'drishyam_2.jpg'
            },
            {
                'name': 'Chhava: The Great Maratha',
                'subtitle': 'Valor of Chhatrapati Sambhaji',
                'genre': 'Drama',
                'language': 'Hindi',
                'rating': Decimal('8.5'),
                'release_date': datetime.date(2024, 12, 6),
                'duration': 160,
                'views_count': 2100,
                'cast': 'Vicky Kaushal, Rashmika Mandanna, Akshaye Khanna, Ashutosh Rana',
                'description': 'An epic historical biographical saga detailing the unmatched courage, military strategy, and resilience of Chhatrapati Sambhaji Maharaj.',
                'color1': (194, 65, 12),
                'color2': (124, 45, 18),
                'img_filename': 'chhava.jpg'
            }
        ]

        # Generate posters and save movies
        created_movies = []
        for m_data in movies_dataset:
            poster_rel_path = f"movies/{m_data['img_filename']}"
            poster_abs_path = os.path.join('media', poster_rel_path)
            generate_movie_poster(
                filepath=poster_abs_path,
                title=m_data['name'],
                subtitle=m_data['subtitle'],
                genre=m_data['genre'],
                lang=m_data['language'],
                rating=str(m_data['rating']),
                color1=m_data['color1'],
                color2=m_data['color2']
            )

            movie_dict = {
                'name': m_data['name'],
                'genre': m_data['genre'],
                'language': m_data['language'],
                'rating': m_data['rating'],
                'release_date': m_data['release_date'],
                'duration': m_data['duration'],
                'views_count': m_data['views_count'],
                'cast': m_data['cast'],
                'description': m_data['description'],
                'image': poster_rel_path
            }

            movie, _ = Movie.objects.update_or_create(
                name=m_data['name'],
                defaults=movie_dict
            )
            created_movies.append(movie)

        # 3. SCHEDULE THEATERS & SHOWTIMES ACROSS 6 CITIES
        cities_theaters = [
            ('Mumbai', [
                ('PVR ICON: Phoenix Palladium Lower Parel', 'PVR', Decimal('350.00')),
                ('INOX: Megaplex Inorbit Mall Malad', 'INOX', Decimal('280.00')),
                ('Cinepolis: Viviana Mall Thane', 'Cinepolis', Decimal('230.00')),
            ]),
            ('Delhi-NCR', [
                ("PVR Director's Cut: Ambience Mall Vasant Kunj", 'PVR', Decimal('450.00')),
                ('INOX: Nehru Place Epicuria', 'INOX', Decimal('270.00')),
                ('Cinepolis: DLF Avenue Saket', 'Cinepolis', Decimal('310.00')),
            ]),
            ('Bengaluru', [
                ('PVR: Forum Mall Koramangala', 'PVR', Decimal('330.00')),
                ('INOX: Garuda Mall MG Road', 'INOX', Decimal('260.00')),
                ('Cinepolis: Orion Mall Rajajinagar', 'Cinepolis', Decimal('220.00')),
            ]),
            ('Hyderabad', [
                ('Prasads Multiplex: Necklace Road', 'Prasads', Decimal('250.00')),
                ('AMB Cinemas: Gachibowli', 'AMB', Decimal('360.00')),
                ('PVR: Next Galleria Mall Punjagutta', 'PVR', Decimal('240.00')),
            ]),
            ('Chennai', [
                ('SPI Sathyam Cinemas: Royapettah', 'SPI', Decimal('200.00')),
                ('PVR: Express Avenue Mall', 'PVR', Decimal('240.00')),
                ('INOX: The Marina Mall OMR', 'INOX', Decimal('190.00')),
            ]),
            ('Pune', [
                ('PVR: Phoenix Marketcity Viman Nagar', 'PVR', Decimal('290.00')),
                ('Cinepolis: Seasons Mall Hadapsar', 'Cinepolis', Decimal('220.00')),
                ('INOX: Bund Garden Road', 'INOX', Decimal('180.00')),
            ])
        ]

        now = timezone.now()
        show_hours = [
            (9, 30),   # Morning
            (11, 15),  # Morning
            (13, 45),  # Afternoon
            (15, 30),  # Afternoon
            (17, 15),  # Evening
            (19, 45),  # Evening
            (21, 30),  # Night
            (22, 45),  # Night
        ]

        total_theaters = 0
        total_seats = 0

        for movie_idx, movie in enumerate(created_movies):
            # Assign 2-3 cities per movie
            assigned_cities = [cities_theaters[i % len(cities_theaters)] for i in range(movie_idx, movie_idx + 3)]
            for city_name, venues in assigned_cities:
                for venue_idx, (venue_name, chain, base_price) in enumerate(venues):
                    hour_idx = (movie_idx + venue_idx) % len(show_hours)
                    hr, mn = show_hours[hour_idx]
                    show_time = now.replace(hour=hr, minute=mn, second=0, microsecond=0) + datetime.timedelta(days=(movie_idx % 3))

                    theater, _ = Theater.objects.get_or_create(
                        name=venue_name,
                        movie=movie,
                        time=show_time,
                        defaults={
                            'city': city_name,
                            'theater_chain': chain,
                            'price': base_price + Decimal(str(hour_idx * 15))
                        }
                    )
                    total_theaters += 1

                    existing_seats = set(theater.seats.values_list('seat_number', flat=True))
                    new_seats = []
                    for row in ['A', 'B', 'C']:
                        for col in range(1, 7):
                            seat_num = f'{row}{col}'
                            if seat_num not in existing_seats:
                                new_seats.append(Seat(theater=theater, seat_number=seat_num, is_booked=False))
                            total_seats += 1
                    if new_seats:
                        Seat.objects.bulk_create(new_seats)

        # 4. PERSONALIZED BOOKINGS & HISTORY FOR 5 INDIAN USERS
        # User 1: Aarav Sharma (Loves Sci-Fi & Action -> Kalki, Interstellar, Dark Knight)
        user_aarav = created_users['aarav_sharma']
        for mov in [created_movies[0], created_movies[2]]:  # Kalki, Interstellar
            th = Theater.objects.filter(movie=mov).first()
            if th:
                st = Seat.objects.filter(theater=th, is_booked=False).first()
                if st:
                    st.is_booked = True
                    st.save()
                    Booking.objects.get_or_create(user=user_aarav, seat=st, movie=mov, theater=th)
        RecentlyViewed.objects.get_or_create(user=user_aarav, movie=created_movies[10]) # Dark Knight

        # User 2: Priya Patel (Loves Comedy & Romance -> Laapataa Ladies, Sita Ramam)
        user_priya = created_users['priya_patel']
        for mov in [created_movies[6], created_movies[13]]:  # Laapataa Ladies, Sita Ramam
            th = Theater.objects.filter(movie=mov).first()
            if th:
                st = Seat.objects.filter(theater=th, is_booked=False).first()
                if st:
                    st.is_booked = True
                    st.save()
                    Booking.objects.get_or_create(user=user_priya, seat=st, movie=mov, theater=th)
        RecentlyViewed.objects.get_or_create(user=user_priya, movie=created_movies[7]) # Stree 2

        # User 3: Rohit Verma (Loves Thriller & Mystery -> Manjummel Boys, Drishyam 2)
        user_rohit = created_users['rohit_verma']
        for mov in [created_movies[5], created_movies[14]]:  # Manjummel Boys, Drishyam 2
            th = Theater.objects.filter(movie=mov).first()
            if th:
                st = Seat.objects.filter(theater=th, is_booked=False).first()
                if st:
                    st.is_booked = True
                    st.save()
                    Booking.objects.get_or_create(user=user_rohit, seat=st, movie=mov, theater=th)
        RecentlyViewed.objects.get_or_create(user=user_rohit, movie=created_movies[11]) # Oppenheimer

        # User 4: Ananya Iyer (Loves South Indian Blockbusters & Drama -> Kantara, Leo)
        user_ananya = created_users['ananya_iyer']
        for mov in [created_movies[8], created_movies[4]]:  # Kantara, Leo
            th = Theater.objects.filter(movie=mov).first()
            if th:
                st = Seat.objects.filter(theater=th, is_booked=False).first()
                if st:
                    st.is_booked = True
                    st.save()
                    Booking.objects.get_or_create(user=user_ananya, seat=st, movie=mov, theater=th)
        RecentlyViewed.objects.get_or_create(user=user_ananya, movie=created_movies[9]) # Pushpa 2

        # User 5: Vikram Singh (Loves High-Octane Action -> Jawan, Pushpa 2)
        user_vikram = created_users['vikram_singh']
        for mov in [created_movies[1], created_movies[9]]:  # Jawan, Pushpa 2
            th = Theater.objects.filter(movie=mov).first()
            if th:
                st = Seat.objects.filter(theater=th, is_booked=False).first()
                if st:
                    st.is_booked = True
                    st.save()
                    Booking.objects.get_or_create(user=user_vikram, seat=st, movie=mov, theater=th)
        RecentlyViewed.objects.get_or_create(user=user_vikram, movie=created_movies[15]) # Chhava

        # 5. SEED 3 HERO BANNER SLIDES
        banners_data = [
            {
                'order': 0,
                'title': 'Discover Blockbuster Experiences',
                'subtitle': 'Filter movies by genre, language, city & theater with real-time showtimes.',
                'badge': 'Now Trending',
                'badge_color': 'danger',
                'button_text': 'Explore All Movies',
                'button_url': '/movies/',
                'color1': (229, 9, 20),
                'color2': (17, 24, 39),
                'filename': 'banner_trending.jpg',
            },
            {
                'order': 1,
                'title': 'Personalized Movie Discovery',
                'subtitle': 'Smart recommendations based on your favourite genres & past bookings.',
                'badge': 'Top Rated',
                'badge_color': 'warning',
                'button_text': 'View Top Rated',
                'button_url': '/movies/?sort=rating',
                'color1': (202, 138, 4),
                'color2': (15, 23, 42),
                'filename': 'banner_top_rated.jpg',
            },
            {
                'order': 2,
                'title': 'Book Shows Across 6 Cities',
                'subtitle': 'PVR, INOX, Cinepolis shows in Mumbai, Delhi, Bengaluru, Hyderabad, Chennai & Pune.',
                'badge': 'Multi-City Shows',
                'badge_color': 'info',
                'button_text': 'Book Now',
                'button_url': '/movies/',
                'color1': (3, 105, 161),
                'color2': (6, 78, 59),
                'filename': 'banner_cities.jpg',
            },
        ]

        for b in banners_data:
            rel_path = f"banners/{b['filename']}"
            abs_path = os.path.join('media', rel_path)
            generate_banner_image(
                filepath=abs_path,
                title=b['title'],
                subtitle=b['subtitle'],
                badge=b['badge'],
                color1=b['color1'],
                color2=b['color2'],
            )
            HeroBanner.objects.update_or_create(
                order=b['order'],
                defaults={
                    'title':       b['title'],
                    'subtitle':    b['subtitle'],
                    'badge':       b['badge'],
                    'badge_color': b['badge_color'],
                    'button_text': b['button_text'],
                    'button_url':  b['button_url'],
                    'is_active':   True,
                    'image':       rel_path,
                }
            )

        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {len(created_movies)} movies with copyright-free posters, '
            f'{total_theaters} shows across 6 cities, 5 Indian user profiles, and 3 hero banner slides!'
        ))

