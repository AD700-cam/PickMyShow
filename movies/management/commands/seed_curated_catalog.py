import os
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from PIL import Image, ImageDraw

from movies.models import (
    Movie, Theater, Seat, Genre, Language,
    CastMember, MoviePoster, Review, Booking, HeroBanner
)


def generate_movie_poster(filepath, title, subtitle, genre, lang, rating, color1, color2):
    """Generates a clean, aesthetic movie poster image using Pillow if it does not already exist."""
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

    # Decorative geometric arches & cinema motifs
    for rad in range(70, 280, 35):
        draw.arc([w // 2 - rad, 220 - rad, w // 2 + rad, 220 + rad], 0, 360, fill=(255, 255, 255, 25), width=2)

    # Dark gradient overlay on bottom half for typography readability
    overlay = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    ov_draw.rectangle([0, h - 350, w, h], fill=(10, 10, 15, 220))
    for gy in range(h - 480, h - 350):
        alpha_v = int(220 * (gy - (h - 480)) / 130)
        ov_draw.line([(0, gy), (w, gy)], fill=(10, 10, 15, alpha_v))

    img_rgba = img.convert('RGBA')
    img_rgba = Image.alpha_composite(img_rgba, overlay)
    img = img_rgba.convert('RGB')
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([0, 0, w, 6], fill=(229, 9, 20))

    # Badge Pill (Genre & Language)
    badge = f"{genre.upper()} • {lang.upper()}"
    bw = len(badge) * 9 + 24
    draw.rounded_rectangle([40, 40, 40 + bw, 72], radius=6, fill=(229, 9, 20))
    draw.text((40 + bw // 2, 56), badge, fill=(255, 255, 255), anchor='mm')

    # Rating badge
    rw = 90
    draw.rounded_rectangle([w - 40 - rw, 40, w - 40, 72], radius=6, fill=(245, 158, 11))
    draw.text((w - 40 - rw // 2, 56), f"★ {rating}", fill=(20, 20, 20), anchor='mm')

    # Movie Title
    draw.text((w // 2, h - 240), title, fill=(255, 255, 255), anchor='mm')

    # Subtitle / Tagline
    draw.text((w // 2, h - 190), subtitle, fill=(200, 215, 235), anchor='mm')

    # Divider bar
    draw.rectangle([w // 2 - 60, h - 160, w // 2 + 60, h - 158], fill=(229, 9, 20))

    # Book Now CTA Pill
    draw.rounded_rectangle([w // 2 - 100, h - 120, w // 2 + 100, h - 75], radius=22, fill=(229, 9, 20))
    draw.text((w // 2, h - 97), '▶ BOOK TICKETS', fill=(255, 255, 255), anchor='mm')

    img.save(filepath, 'JPEG', quality=90)


class Command(BaseCommand):
    help = "Seeds and optimizes the catalog to exactly 20 rich movies with 5 proper screening events per movie"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting catalog optimization: 20 Movies, 5 Events per Movie..."))

        # 1. Standard Genres & Languages
        genres_data = [
            ('Action', 'fa-fire', 'High octane explosions, combat, and thrill.'),
            ('Sci-Fi', 'fa-rocket', 'Futuristic exploration, time travel, and advanced technology.'),
            ('Drama', 'fa-theater-masks', 'Compelling emotional narratives and human stories.'),
            ('Comedy', 'fa-laugh-beam', 'Humor, satire, and lighthearted entertainment.'),
            ('Thriller', 'fa-skull', 'Suspense, mystery, and high stakes danger.'),
            ('Fantasy', 'fa-dragon', 'Mythical beings, magical realms, and heroic legends.'),
            ('Horror', 'fa-ghost', 'Spine-chilling terror and supernatural mysteries.'),
            ('Romance', 'fa-heart', 'Passionate love stories and heartfelt connections.'),
            ('Adventure', 'fa-compass', 'Epic journeys across uncharted worlds.'),
            ('Animation', 'fa-palette', 'Stunning animated artistry for all ages.'),
        ]
        genres_map = {}
        for name, icon, desc in genres_data:
            g, _ = Genre.objects.get_or_create(name=name, defaults={'icon': icon, 'description': desc})
            genres_map[name] = g

        languages_data = [
            ('English', 'en'),
            ('Hindi', 'hi'),
            ('Tamil', 'ta'),
            ('Telugu', 'te'),
            ('Malayalam', 'ml'),
            ('Kannada', 'kn'),
        ]
        lang_map = {}
        for name, code in languages_data:
            l, _ = Language.objects.get_or_create(name=name, defaults={'code': code})
            lang_map[name] = l

        # 2. Curated 20 Movies Specification
        curated_movies = [
            {
                'name': 'Kalki 2898 AD',
                'subtitle': 'A Modern Sci-Fi Epoch',
                'genre': 'Sci-Fi',
                'language': 'Telugu',
                'rating': Decimal('8.8'),
                'release_date': datetime.date(2024, 6, 27),
                'duration': 181,
                'views_count': 4200,
                'cast': 'Prabhas, Amitabh Bachchan, Kamal Haasan, Deepika Padukone',
                'director': 'Nag Ashwin',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=y1-w1TrFmoQ',
                'description': 'In the dystopian future city of Kasi, an ancient warrior rises to protect the unborn vessel of the final avatar from a totalitarian god-king.',
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
                'views_count': 3800,
                'cast': 'Shah Rukh Khan, Nayanthara, Vijay Sethupathi, Deepika Padukone',
                'director': 'Atlee',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=COv52Qyctws',
                'description': 'A high-octane emotional action thriller of a man driven by personal vendetta to right societal wrongs and fulfill an old promise.',
                'color1': (127, 29, 29),
                'color2': (17, 24, 39),
                'img_filename': 'jawan.jpg'
            },
            {
                'name': 'Interstellar',
                'subtitle': 'Beyond Space and Time',
                'genre': 'Sci-Fi',
                'language': 'English',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2024, 1, 15),
                'duration': 169,
                'views_count': 3600,
                'cast': 'Matthew McConaughey, Anne Hathaway, Jessica Chastain, Michael Caine',
                'director': 'Christopher Nolan',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=zSWdZVtXT7E',
                'description': 'When Earth becomes uninhabitable, a pilot leads an expedition across a spatial wormhole near Saturn to ensure humanity\'s survival.',
                'color1': (10, 15, 30),
                'color2': (30, 58, 138),
                'img_filename': 'interstellar.jpg'
            },
            {
                'name': 'Inception',
                'subtitle': 'Your Mind Is The Scene Of The Crime',
                'genre': 'Sci-Fi',
                'language': 'English',
                'rating': Decimal('8.8'),
                'release_date': datetime.date(2023, 10, 1),
                'duration': 148,
                'views_count': 3500,
                'cast': 'Leonardo DiCaprio, Joseph Gordon-Levitt, Elliot Page, Tom Hardy',
                'director': 'Christopher Nolan',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=YoHD9XEInc0',
                'description': 'A skilled corporate thief who steals secrets from deep within the subconscious during dream states is tasked with the impossible: planting an idea.',
                'color1': (20, 30, 48),
                'color2': (36, 59, 85),
                'img_filename': 'inception.jpg'
            },
            {
                'name': 'Brahmastra: Part One - Shiva',
                'subtitle': 'The Legend of the Astras',
                'genre': 'Fantasy',
                'language': 'Hindi',
                'rating': Decimal('8.1'),
                'release_date': datetime.date(2023, 9, 9),
                'duration': 167,
                'views_count': 2900,
                'cast': 'Ranbir Kapoor, Alia Bhatt, Amitabh Bachchan, Nagarjuna Akkineni',
                'director': 'Ayan Mukerji',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=V5Z64h1_e70',
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
                'views_count': 3100,
                'cast': 'Thalapathy Vijay, Sanjay Dutt, Trisha Krishnan, Arjun Sarja',
                'director': 'Lokesh Kanagaraj',
                'cert': 'A',
                'trailer': 'https://www.youtube.com/watch?v=Po3jStA673E',
                'description': 'A calm cafe owner in Kashmir is hunted by notorious mobsters who insist he is their long-lost feared underworld enforcer Leo Das.',
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
                'views_count': 3200,
                'cast': 'Soubin Shahir, Sreenath Bhasi, Balu Varghese, Ganapathi',
                'director': 'Chidambaram',
                'cert': 'U',
                'trailer': 'https://www.youtube.com/watch?v=0kE2dI0mF8g',
                'description': 'A tight-knit group of friends face an impossible rescue mission in the perilous depths of the forbidden Guna Caves.',
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
                'views_count': 2600,
                'cast': 'Nitanshi Goel, Pratibha Ranta, Sparsh Shrivastava, Ravi Kishan',
                'director': 'Kiran Rao',
                'cert': 'U',
                'trailer': 'https://www.youtube.com/watch?v=2sm_hVq_kL0',
                'description': 'A delightful comedy of errors unfolds in rural India when two young veiled brides are accidentally swapped on a crowded train.',
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
                'views_count': 3700,
                'cast': 'Rajkummar Rao, Shraddha Kapoor, Pankaj Tripathi, Abhishek Banerjee',
                'director': 'Amar Kaushik',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=y3n5N2RjG7g',
                'description': 'The beloved town of Chanderi faces a sinister new entity named Sarkata, uniting the gang with the supernatural protector Stree.',
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
                'views_count': 3300,
                'cast': 'Rishab Shetty, Sapthami Gowda, Kishore, Achyuth Kumar',
                'director': 'Rishab Shetty',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=8mrVmf239GU',
                'description': 'In a coastal hamlet, a fierce rebellion of nature and ancestral spirits erupts as a tribal youth confronts ruthless forest encroachment.',
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
                'views_count': 4500,
                'cast': 'Allu Arjun, Rashmika Mandanna, Fahadh Faasil, Jagapathi Babu',
                'director': 'Sukumar',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=g3JUbgOHgdw',
                'description': 'Pushpa Raj cements his reign over the red sandalwood empire while fighting fierce international syndicates and relentless police enforcement.',
                'color1': (185, 28, 28),
                'color2': (67, 20, 7),
                'img_filename': 'pushpa_2.jpg'
            },
            {
                'name': 'The Dark Knight',
                'subtitle': 'Guardian of the Night',
                'genre': 'Action',
                'language': 'English',
                'rating': Decimal('9.0'),
                'release_date': datetime.date(2023, 8, 20),
                'duration': 152,
                'views_count': 3900,
                'cast': 'Christian Bale, Heath Ledger, Aaron Eckhart, Gary Oldman',
                'director': 'Christopher Nolan',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=EXeTwQWrcwY',
                'description': 'Batman faces his ultimate psychological and ideological nemesis in the form of the chaotic Joker who threatens to dismantle Gotham.',
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
                'views_count': 3400,
                'cast': 'Cillian Murphy, Emily Blunt, Matt Damon, Robert Downey Jr.',
                'director': 'Christopher Nolan',
                'cert': 'R',
                'trailer': 'https://www.youtube.com/watch?v=uYPbbksJxIg',
                'description': 'The riveting historical chronicle of J. Robert Oppenheimer leading the top-secret Manhattan Project to create the first atomic weapon.',
                'color1': (217, 119, 6),
                'color2': (24, 24, 27),
                'img_filename': 'oppenheimer.jpg'
            },
            {
                'name': 'Spider-Man: Brand New Day',
                'subtitle': 'A Hero Reborn',
                'genre': 'Adventure',
                'language': 'English',
                'rating': Decimal('8.7'),
                'release_date': datetime.date(2024, 5, 3),
                'duration': 140,
                'views_count': 3100,
                'cast': 'Tom Holland, Zendaya, Jacob Batalon, Benedict Cumberbatch',
                'director': 'Jon Watts',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=JfVOs4VSpmA',
                'description': 'Peter Parker navigates life with his secret identity erased from the world\'s memory, confronting a powerful underground crime boss.',
                'color1': (190, 18, 60),
                'color2': (30, 58, 138),
                'img_filename': 'Spider-Man_Brand_New_Day.jpg'
            },
            {
                'name': 'RRR: Rise Roar Revolt',
                'subtitle': 'Fire and Water Collide',
                'genre': 'Action',
                'language': 'Telugu',
                'rating': Decimal('8.8'),
                'release_date': datetime.date(2023, 3, 25),
                'duration': 187,
                'views_count': 3800,
                'cast': 'N.T. Rama Rao Jr., Ram Charan, Alia Bhatt, Ajay Devgn',
                'director': 'S.S. Rajamouli',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=NgBoMJy386M',
                'description': 'A fearless warrior and a disciplined officer in 1920s colonial India form an unshakeable bond before discovering their fateful opposing missions.',
                'color1': (217, 119, 6),
                'color2': (30, 58, 138),
                'img_filename': 'rrr.jpg'
            },
            {
                'name': 'Sita Ramam: A Love Story',
                'subtitle': 'Love Across The Battlefield',
                'genre': 'Romance',
                'language': 'Telugu',
                'rating': Decimal('8.5'),
                'release_date': datetime.date(2023, 8, 5),
                'duration': 163,
                'views_count': 2700,
                'cast': 'Dulquer Salmaan, Mrunal Thakur, Rashmika Mandanna, Sumanth',
                'director': 'Hanu Raghavapudi',
                'cert': 'U',
                'trailer': 'https://www.youtube.com/watch?v=Q8Fw8zXn0-8',
                'description': 'An orphaned army lieutenant serving at the Kashmir border receives heartfelt letters from an enigmatic woman named Sita, sparking a timeless romance.',
                'color1': (190, 24, 93),
                'color2': (67, 56, 202),
                'img_filename': 'sita_ramam.jpg'
            },
            {
                'name': 'The Odyssey',
                'subtitle': 'The Epic of Ithaka',
                'genre': 'Action',
                'language': 'English',
                'rating': Decimal('8.5'),
                'release_date': datetime.date(2024, 4, 12),
                'duration': 155,
                'views_count': 2500,
                'cast': 'Armand Assante, Greta Scacchi, Isabella Rossellini, Christopher Lee',
                'director': 'Andrei Konchalovsky',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=1F3d1vCg2xM',
                'description': 'Odysseus embarks on a treacherous ten-year voyage across tempestuous seas, battling mythical monsters and divine wrath to return home.',
                'color1': (14, 116, 144),
                'color2': (15, 23, 42),
                'img_filename': 'The_Odyssey.jpg'
            },
            {
                'name': 'Drishyam 2: The Resumption',
                'subtitle': 'Guilt, Secrets & Family',
                'genre': 'Thriller',
                'language': 'Hindi',
                'rating': Decimal('8.6'),
                'release_date': datetime.date(2023, 11, 18),
                'duration': 140,
                'views_count': 3200,
                'cast': 'Ajay Devgn, Tabu, Akshaye Khanna, Shriya Saran',
                'director': 'Abhishek Pathak',
                'cert': 'UA 13+',
                'trailer': 'https://www.youtube.com/watch?v=b0wF1kQd_78',
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
                'views_count': 2800,
                'cast': 'Vicky Kaushal, Rashmika Mandanna, Akshaye Khanna, Ashutosh Rana',
                'director': 'Laxman Utekar',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=5U9bT2rC1kM',
                'description': 'An epic historical biographical saga detailing the unmatched courage, military strategy, and resilience of Chhatrapati Sambhaji Maharaj.',
                'color1': (194, 65, 12),
                'color2': (124, 45, 18),
                'img_filename': 'chhava.jpg'
            },
            {
                'name': 'Dune: Part Two',
                'subtitle': 'Long Live The Fighters',
                'genre': 'Sci-Fi',
                'language': 'English',
                'rating': Decimal('8.9'),
                'release_date': datetime.date(2024, 3, 1),
                'duration': 166,
                'views_count': 3600,
                'cast': 'Timothée Chalamet, Zendaya, Rebecca Ferguson, Javier Bardem',
                'director': 'Denis Villeneuve',
                'cert': 'UA 16+',
                'trailer': 'https://www.youtube.com/watch?v=Way9Dexny3w',
                'description': 'Paul Atreides unites with Chani and the Fremen while seeking vengeance against the conspirators who destroyed his family, striving to prevent a catastrophic holy war.',
                'color1': (202, 138, 4),
                'color2': (67, 20, 7),
                'img_filename': 'dune_2.jpg'
            }
        ]

        # 3. Create or Update 20 Movies
        saved_movies = []
        for m_data in curated_movies:
            poster_rel = f"movies/{m_data['img_filename']}"
            poster_abs = os.path.join('media', poster_rel)
            generate_movie_poster(
                filepath=poster_abs,
                title=m_data['name'],
                subtitle=m_data['subtitle'],
                genre=m_data['genre'],
                lang=m_data['language'],
                rating=str(m_data['rating']),
                color1=m_data['color1'],
                color2=m_data['color2']
            )

            movie, _ = Movie.objects.update_or_create(
                name=m_data['name'],
                defaults={
                    'genre': m_data['genre'],
                    'language': m_data['language'],
                    'rating': m_data['rating'],
                    'release_date': m_data['release_date'],
                    'duration': m_data['duration'],
                    'views_count': m_data['views_count'],
                    'cast': m_data['cast'],
                    'director': m_data['director'],
                    'age_certification': m_data['cert'],
                    'trailer_url': m_data['trailer'],
                    'description': m_data['description'],
                    'image': poster_rel
                }
            )

            # Link M2M Genre & Language
            if m_data['genre'] in genres_map:
                movie.genres.add(genres_map[m_data['genre']])
            if m_data['language'] in lang_map:
                movie.languages.add(lang_map[m_data['language']])

            saved_movies.append(movie)

        self.stdout.write(self.style.SUCCESS(f"Successfully verified {len(saved_movies)} movies in catalog."))

        # 4. Scheduling 5 Screening Events per Movie
        # Each event is tied to proper places (theaters & cities), times, screen formats, and prices.
        now = timezone.now()
        base_today = now.replace(second=0, microsecond=0)

        # 5 distinct event templates across top cities and premier theater chains
        event_templates = [
            {
                'slot': 'Morning Show',
                'hour': 10, 'minute': 0,
                'name': 'PVR ICON: Phoenix Palladium Lower Parel',
                'city': 'Mumbai',
                'chain': 'PVR',
                'screen': 'Audi 1 - 4K Laser Standard',
                'price': Decimal('200.00'),
                'day_offset': 0,
            },
            {
                'slot': 'Matinee Show',
                'hour': 13, 'minute': 30,
                'name': 'INOX: Megaplex Inorbit Mall Malad',
                'city': 'Mumbai',
                'chain': 'INOX',
                'screen': 'Audi 2 - Dolby Atmos 7.1',
                'price': Decimal('280.00'),
                'day_offset': 0,
            },
            {
                'slot': 'Afternoon Show',
                'hour': 16, 'minute': 45,
                'name': 'Cinepolis: DLF Avenue Saket',
                'city': 'Delhi-NCR',
                'chain': 'Cinepolis',
                'screen': 'Audi 3 - 4DX RealMotion 3D',
                'price': Decimal('360.00'),
                'day_offset': 0,
            },
            {
                'slot': 'Prime Evening Show',
                'hour': 19, 'minute': 30,
                'name': 'Prasads Multiplex: Necklace Road',
                'city': 'Hyderabad',
                'chain': 'Prasads',
                'screen': 'Audi 4 - IMAX Laser Dual 4K',
                'price': Decimal('450.00'),
                'day_offset': 0,
            },
            {
                'slot': 'Late Night Blockbuster',
                'hour': 22, 'minute': 15,
                'name': 'AMB Cinemas: Gachibowli',
                'city': 'Hyderabad',
                'chain': 'AMB',
                'screen': 'Audi 5 - VIP Gold Class Recliner',
                'price': Decimal('550.00'),
                'day_offset': 0,
            },
        ]

        total_new_events = 0
        total_new_seats = 0

        # Schedule across upcoming days (Tomorrow & Day after tomorrow)
        # Guarantees that EVERY single movie has strictly upcoming active events ready for booking
        tomorrow = base_today + datetime.timedelta(days=1)
        day_after = base_today + datetime.timedelta(days=2)

        for movie in saved_movies:
            # Schedule 5 primary events for tomorrow
            for ev in event_templates:
                for target_date in [tomorrow, day_after]:
                    event_time = target_date.replace(
                        hour=ev['hour'],
                        minute=ev['minute']
                    )

                    theater, created = Theater.objects.get_or_create(
                        name=ev['name'],
                        movie=movie,
                        time=event_time,
                        defaults={
                            'city': ev['city'],
                            'theater_chain': ev['chain'],
                            'screen_name': ev['screen'],
                            'price': ev['price']
                        }
                    )

                    if created:
                        total_new_events += 1

                    # Generate seating plan: 48 seats (Rows A-F, cols 1-8)
                    existing_seat_count = theater.seats.count()
                    if existing_seat_count < 48:
                        existing_numbers = set(theater.seats.values_list('seat_number', flat=True))
                        seats_to_create = []

                        for row in ['A', 'B', 'C', 'D', 'E', 'F']:
                            for col in range(1, 9):
                                s_num = f"{row}{col}"
                                if s_num not in existing_numbers:
                                    # Mark ~20% of seats as realistically booked
                                    is_booked = (col in [3, 7] and row in ['C', 'D'])
                                    seats_to_create.append(Seat(
                                        theater=theater,
                                        seat_number=s_num,
                                        is_booked=is_booked
                                    ))

                        if seats_to_create:
                            Seat.objects.bulk_create(seats_to_create)
                            total_new_seats += len(seats_to_create)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully scheduled screening events! Total active movies: {len(saved_movies)}, "
            f"new events: {total_new_events}, new seats: {total_new_seats}"
        ))

        # 5. Seed Curated Hero Carousel Banners
        self.stdout.write(self.style.NOTICE("Seeding Hero Carousel Banners..."))
        kalki_mov = Movie.objects.filter(name__icontains='Kalki').first()
        oppen_mov = Movie.objects.filter(name__icontains='Oppenheimer').first()
        incept_mov = Movie.objects.filter(name__icontains='Inception').first()
        kantara_mov = Movie.objects.filter(name__icontains='Kantara').first()
        manjummel_mov = Movie.objects.filter(name__icontains='Manjummel').first()

        banners_config = [
            {
                'order': 0,
                'title': 'Kalki 2898 AD',
                'subtitle': 'The Mythological Dystopian Epic | In Cinemas Now',
                'badge': 'Now Trending',
                'badge_color': 'danger',
                'image': 'banners/Kalki_2898_AD.png',
                'button_text': 'Book Tickets',
                'button_url': f'/movies/{kalki_mov.id}/theaters/' if kalki_mov else '/movies/',
            },
            {
                'order': 1,
                'title': 'Oppenheimer: The Atomic Dawn',
                'subtitle': "Experience Christopher Nolan's Masterpiece in IMAX 70mm",
                'badge': 'Top Rated',
                'badge_color': 'warning',
                'image': 'banners/oppenheimer.png',
                'button_text': 'Book Tickets',
                'button_url': f'/movies/{oppen_mov.id}/theaters/' if oppen_mov else '/movies/',
            },
            {
                'order': 2,
                'title': 'Inception: 15th Anniversary',
                'subtitle': 'Your Mind is the Scene of the Crime | Special Screening',
                'badge': 'Now Trending',
                'badge_color': 'danger',
                'image': 'banners/insepstion.png',
                'button_text': 'Reserve Seats',
                'button_url': f'/movies/{incept_mov.id}/theaters/' if incept_mov else '/movies/',
            },
            {
                'order': 3,
                'title': 'Kantara: A Legend',
                'subtitle': 'Divine Myth and Fierce Pride | Sensational Folk Action',
                'badge': 'Top Rated',
                'badge_color': 'warning',
                'image': 'banners/Kantara_A_Legend.png',
                'button_text': 'Book Tickets',
                'button_url': f'/movies/{kantara_mov.id}/theaters/' if kantara_mov else '/movies/',
            },
            {
                'order': 4,
                'title': 'Manjummel Boys',
                'subtitle': 'Friendship Unshaken | The Survival Thriller of the Year',
                'badge': 'New Release',
                'badge_color': 'success',
                'image': 'banners/Manjummel_Boys.png',
                'button_text': 'Book Now',
                'button_url': f'/movies/{manjummel_mov.id}/theaters/' if manjummel_mov else '/movies/',
            },
            {
                'order': 5,
                'title': 'Multi-City Multiplex Network',
                'subtitle': 'Book 4K Laser, Dolby Atmos & IMAX shows across Mumbai, Delhi-NCR & Hyderabad',
                'badge': 'Multi-City',
                'badge_color': 'info',
                'image': 'banners/banner_cities.jpg',
                'button_text': 'Explore Theaters',
                'button_url': '/movies/',
            },
        ]

        for b in banners_config:
            HeroBanner.objects.update_or_create(
                order=b['order'],
                defaults={
                    'title': b['title'],
                    'subtitle': b['subtitle'],
                    'badge': b['badge'],
                    'badge_color': b['badge_color'],
                    'image': b['image'],
                    'button_text': b['button_text'],
                    'button_url': b['button_url'],
                    'is_active': True,
                }
            )
        self.stdout.write(self.style.SUCCESS(f"Successfully seeded {len(banners_config)} Hero Banners!"))
