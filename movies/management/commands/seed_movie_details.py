import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction
from movies.models import Movie, Genre, Language, CastMember, MoviePoster, Review, Booking, Theater, Seat


class Command(BaseCommand):
    help = "Populates trailers, age certifications, cast members, genres, languages, and sample reviews for movies"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding Genres and Languages...")

        # 1. Genres
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

        # 2. Languages
        languages_data = [
            ('English', 'en'),
            ('Hindi', 'hi'),
            ('Tamil', 'ta'),
            ('Telugu', 'te'),
            ('Malayalam', 'ml'),
            ('Kannada', 'kn'),
            ('Spanish', 'es'),
            ('French', 'fr'),
        ]
        lang_map = {}
        for name, code in languages_data:
            l, _ = Language.objects.get_or_create(name=name, defaults={'code': code})
            lang_map[name] = l

        # 3. Movie details enhancement dictionary
        details = {
            'Interstellar Odyssey': {
                'trailer': 'https://www.youtube.com/watch?v=zSWdZVtXT7E',
                'cert': 'UA 13+',
                'director': 'Christopher Nolan',
                'synopsis': 'When environmental collapse threatens human existence, an ex-NASA pilot and astrophysicist travels through an unexplained spatial wormhole near Saturn in search of habitable planets for humanity.',
                'cast': [
                    ('Matthew McConaughey', 'Lead Actor', 'Cooper'),
                    ('Anne Hathaway', 'Lead Actress', 'Dr. Amelia Brand'),
                    ('Jessica Chastain', 'Supporting Actress', 'Murph Cooper'),
                    ('Michael Caine', 'Supporting Actor', 'Professor Brand'),
                ]
            },
            'Interstellar': {
                'trailer': 'https://www.youtube.com/watch?v=zSWdZVtXT7E',
                'cert': 'UA 13+',
                'director': 'Christopher Nolan',
                'synopsis': 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity\'s survival.',
                'cast': [
                    ('Matthew McConaughey', 'Lead Actor', 'Cooper'),
                    ('Anne Hathaway', 'Lead Actress', 'Dr. Amelia Brand'),
                ]
            },
            'The Dark Knight of Gotham': {
                'trailer': 'https://www.youtube.com/watch?v=EXeTwQWrcwY',
                'cert': 'UA 16+',
                'director': 'Christopher Nolan',
                'synopsis': 'When the menace known as the Joker wreaks havoc and chaos on the people of Gotham, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.',
                'cast': [
                    ('Christian Bale', 'Lead Actor', 'Bruce Wayne / Batman'),
                    ('Heath Ledger', 'Lead Actor', 'The Joker'),
                    ('Gary Oldman', 'Supporting Actor', 'Jim Gordon'),
                    ('Michael Caine', 'Supporting Actor', 'Alfred Pennyworth'),
                ]
            },
            'Inception': {
                'trailer': 'https://www.youtube.com/watch?v=YoHD9XEInc0',
                'cert': 'UA 13+',
                'director': 'Christopher Nolan',
                'synopsis': 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.',
                'cast': [
                    ('Leonardo DiCaprio', 'Lead Actor', 'Dom Cobb'),
                    ('Joseph Gordon-Levitt', 'Supporting Actor', 'Arthur'),
                    ('Elliot Page', 'Supporting Actress', 'Ariadne'),
                    ('Tom Hardy', 'Supporting Actor', 'Eames'),
                ]
            },
            'Brahmastra: Part One - Shiva': {
                'trailer': 'https://www.youtube.com/watch?v=V5Z64h1_e70',
                'cert': 'UA 13+',
                'director': 'Ayan Mukerji',
                'synopsis': 'A young DJ named Shiva embarks on a journey of love and self-discovery when he realizes he has a mysterious connection to fire and holds the power to awaken the ultimate weapon of the gods.',
                'cast': [
                    ('Ranbir Kapoor', 'Lead Actor', 'Shiva'),
                    ('Alia Bhatt', 'Lead Actress', 'Isha'),
                    ('Amitabh Bachchan', 'Supporting Actor', 'Guru Arvind'),
                    ('Nagarjuna Akkineni', 'Supporting Actor', 'Anish Shetty'),
                ]
            },
            'Leo: Bloody Sweet': {
                'trailer': 'https://www.youtube.com/watch?v=Po3jStA673E',
                'cert': 'A',
                'director': 'Lokesh Kanagaraj',
                'synopsis': 'Parthiban is a mild-mannered cafe owner in Himachal Pradesh who becomes an overnight hero after defending his town, only to be targeted by violent gangsters who claim he is a legendary underworld hitman named Leo Das.',
                'cast': [
                    ('Thalapathy Vijay', 'Lead Actor', 'Parthiban / Leo Das'),
                    ('Sanjay Dutt', 'Supporting Actor', 'Antony Das'),
                    ('Trisha Krishnan', 'Lead Actress', 'Sathya'),
                    ('Arjun Sarja', 'Supporting Actor', 'Harold Das'),
                ]
            },
            'Manjummel Boys': {
                'trailer': 'https://www.youtube.com/watch?v=0kE2dI0mF8g',
                'cert': 'U',
                'director': 'Chidambaram',
                'synopsis': 'A group of daring friends from a small town travel to Kodaikanal for a holiday trip, where one of them accidentally falls deep into the subterranean chambers of the notorious Guna Caves, triggering a heroic rescue against all odds.',
                'cast': [
                    ('Soubin Shahir', 'Lead Actor', 'Kuttan'),
                    ('Sreenath Bhasi', 'Lead Actor', 'Subhash'),
                    ('Balu Varghese', 'Supporting Actor', 'Sixen'),
                    ('Ganapathi', 'Supporting Actor', 'Dr. Abhilash'),
                ]
            },
            'Kalki 2898 AD': {
                'trailer': 'https://www.youtube.com/watch?v=y1-w1TrFmoQ',
                'cert': 'UA 13+',
                'director': 'Nag Ashwin',
                'synopsis': 'Set in a post-apocalyptic future in the year 2898 AD, a battle between cosmic forces begins when the immortal warrior Ashwatthama rises to protect the bearer of the tenth avatar of Vishnu from a tyrannical supreme overlord.',
                'cast': [
                    ('Prabhas', 'Lead Actor', 'Bhairava'),
                    ('Amitabh Bachchan', 'Lead Actor', 'Ashwatthama'),
                    ('Kamal Haasan', 'Supporting Actor', 'Supreme Yaskin'),
                    ('Deepika Padukone', 'Lead Actress', 'SUM-80'),
                ]
            },
            'Jawan': {
                'trailer': 'https://www.youtube.com/watch?v=COv52Qyctws',
                'cert': 'UA 16+',
                'director': 'Atlee',
                'synopsis': 'A high-stakes emotional journey of a prison warden driven by a personal vendetta to rectify the wrongs in society, while honoring a promise made to his past.',
                'cast': [
                    ('Shah Rukh Khan', 'Lead Actor', 'Vikram Rathore / Azad'),
                    ('Nayanthara', 'Lead Actress', 'Narmada Rai'),
                    ('Vijay Sethupathi', 'Supporting Actor', 'Kalee Gaikwad'),
                ]
            },
            'RRR: Rise Roar Revolt': {
                'trailer': 'https://www.youtube.com/watch?v=NgBoMJy386M',
                'cert': 'UA 16+',
                'director': 'S.S. Rajamouli',
                'synopsis': 'A fictitious story about two legendary revolutionaries and their journey away from home before they began fighting for their country in the 1920s.',
                'cast': [
                    ('N.T. Rama Rao Jr.', 'Lead Actor', 'Komaram Bheem'),
                    ('Ram Charan', 'Lead Actor', 'Alluri Sitarama Raju'),
                    ('Alia Bhatt', 'Supporting Actress', 'Sita'),
                ]
            },
            'Oppenheimer: The Atomic Dawn': {
                'trailer': 'https://www.youtube.com/watch?v=uYPbbksJxIg',
                'cert': 'R',
                'director': 'Christopher Nolan',
                'synopsis': 'The story of American scientist J. Robert Oppenheimer and his role in the development of the atomic bomb during World War II.',
                'cast': [
                    ('Cillian Murphy', 'Lead Actor', 'J. Robert Oppenheimer'),
                    ('Emily Blunt', 'Lead Actress', 'Katherine Oppenheimer'),
                    ('Robert Downey Jr.', 'Supporting Actor', 'Lewis Strauss'),
                ]
            },
            'Stree 2: Sarkate Ka Aatank': {
                'trailer': 'https://www.youtube.com/watch?v=y3n5N2RjG7g',
                'cert': 'UA 16+',
                'director': 'Amar Kaushik',
                'synopsis': 'The town of Chanderi is haunted once again, this time by a terrifying headless entity named Sarkata that preys on women.',
                'cast': [
                    ('Rajkummar Rao', 'Lead Actor', 'Vicky'),
                    ('Shraddha Kapoor', 'Lead Actress', 'The Unknown Woman'),
                    ('Pankaj Tripathi', 'Supporting Actor', 'Rudra'),
                ]
            },
            'Laapataa Ladies': {
                'trailer': 'https://www.youtube.com/watch?v=2sm_hVq_kL0',
                'cert': 'U',
                'director': 'Kiran Rao',
                'synopsis': 'In rural India, two young brides accidentally get swapped on a train journey, setting off a hilarious and poignant search.',
                'cast': [
                    ('Nitanshi Goel', 'Lead Actress', 'Phool'),
                    ('Pratibha Ranta', 'Lead Actress', 'Jaya'),
                    ('Sparsh Shrivastava', 'Lead Actor', 'Deepak'),
                    ('Ravi Kishan', 'Supporting Actor', 'Inspector Shyam Manohar'),
                ]
            },
            'Kantara: A Legend': {
                'trailer': 'https://www.youtube.com/watch?v=8mrVmf239GU',
                'cert': 'UA 16+',
                'director': 'Rishab Shetty',
                'synopsis': 'When greed paves the way for betrayal and wrath, a young tribal champion invokes the ancient spirit of Daiva to defend his forest and heritage.',
                'cast': [
                    ('Rishab Shetty', 'Lead Actor', 'Shiva'),
                    ('Sapthami Gowda', 'Lead Actress', 'Leela'),
                    ('Kishore', 'Supporting Actor', 'Muralidhar'),
                ]
            }
        }

        # Apply enhancements
        for movie in Movie.objects.all():
            m_info = details.get(movie.name)
            if not m_info:
                # Default values for any other movie
                movie.age_certification = 'UA 13+'
                movie.director = movie.director or 'Acclaimed Director'
                movie.synopsis = movie.synopsis or movie.description or 'An enthralling cinematic experience.'
                movie.trailer_url = movie.trailer_url or 'https://www.youtube.com/watch?v=zSWdZVtXT7E'
            else:
                movie.age_certification = m_info.get('cert', 'UA 13+')
                movie.director = m_info.get('director')
                movie.synopsis = m_info.get('synopsis')
                movie.trailer_url = m_info.get('trailer')

            movie.save()

            # Link genres & languages M2M
            if movie.genre in genres_map:
                movie.genres.add(genres_map[movie.genre])
            if movie.language in lang_map:
                movie.languages.add(lang_map[movie.language])

            # Seed Cast Members
            if m_info and 'cast' in m_info:
                for idx, (c_name, c_role, c_char) in enumerate(m_info['cast']):
                    CastMember.objects.get_or_create(
                        movie=movie,
                        name=c_name,
                        defaults={
                            'role': c_role,
                            'character_name': c_char,
                            'order': idx
                        }
                    )

            # Seed Posters if none exist
            if not movie.posters.exists() and movie.image:
                MoviePoster.objects.create(
                    movie=movie,
                    image=movie.image,
                    caption=f"{movie.name} Official Theatrical Release Poster",
                    is_primary=True,
                    order=0
                )

        # 4. Seed Verified Reviews from Past Bookings
        test_user, _ = User.objects.get_or_create(username='cinephile_alex', defaults={'email': 'alex@example.com'})
        reviewer_sam, _ = User.objects.get_or_create(username='movie_guru_sam', defaults={'email': 'sam@example.com'})

        # Find or create a past showtime so reviews are verified
        now = timezone.now()
        yesterday_show = now - datetime.timedelta(days=1)

        sample_reviews = [
            (
                'Interstellar Odyssey',
                reviewer_sam,
                10,
                'Unbelievable Visual & Musical Mastery!',
                'Watching this on the big screen with IMAX audio was a transcendent experience. Zimmer’s organ score combined with the sheer scale of the gargantua black hole left the entire hall speechless. Must watch for any sci-fi lover!'
            ),
            (
                'Interstellar Odyssey',
                test_user,
                9,
                'Emotional storytelling at cosmic scale',
                'The father-daughter relationship across time dilation is the beating heart of this film. TARS and CASE also provide great humor throughout the journey.'
            ),
            (
                'Brahmastra: Part One - Shiva',
                test_user,
                8,
                'Spectacular visual effects for Indian Cinema',
                'The VFX and background score are top notch. A solid fantasy adventure that sets a promising foundation for the Astraverse.'
            ),
            (
                'Manjummel Boys',
                reviewer_sam,
                9,
                'Edge-of-the-seat survival thriller!',
                'Realistic, raw, and deeply moving tribute to friendship. The cinematography inside the cave sequences is terrifyingly authentic.'
            ),
            (
                'Leo: Bloody Sweet',
                test_user,
                8,
                'Thalapathy Vijay shines in high-octane action',
                'The cafe fight scene and interval block were peak cinema. Anirudh’s score elevates every single punch.'
            )
        ]

        for m_name, user_obj, rating_num, h_line, rev_body in sample_reviews:
            movie_obj = Movie.objects.filter(name__icontains=m_name).first()
            if not movie_obj:
                continue

            # Ensure user has a past booking to be verified
            theater_obj = movie_obj.theaters.first()
            if not theater_obj:
                theater_obj = Theater.objects.create(
                    movie=movie_obj,
                    name='PVR ICON Cinemas',
                    city='Mumbai',
                    screen_name='IMAX Screen 1',
                    theater_chain='PVR',
                    time=yesterday_show,
                    price=Decimal('350.00')
                )
            else:
                # Update theater time to be in past for verification test
                if theater_obj.time > now:
                    theater_obj.time = yesterday_show
                    theater_obj.save(update_fields=['time'])

            booking_obj = Booking.objects.filter(user=user_obj, movie=movie_obj, theater=theater_obj).first()
            if not booking_obj:
                seat_num = f"V{user_obj.id}{movie_obj.id}"[:8]
                # Delete any existing seat with this seat_num in theater if unbooked
                Seat.objects.filter(theater=theater_obj, seat_number=seat_num, booking__isnull=True).delete()
                seat_obj = Seat.objects.create(theater=theater_obj, seat_number=seat_num, is_booked=True)
                booking_obj = Booking.objects.create(
                    user=user_obj,
                    movie=movie_obj,
                    theater=theater_obj,
                    seat=seat_obj,
                    total_price=theater_obj.price,
                    payment_status='CONFIRMED'
                )

            rev, created = Review.objects.update_or_create(
                movie=movie_obj,
                user=user_obj,
                defaults={
                    'booking': booking_obj,
                    'rating': rating_num,
                    'headline': h_line,
                    'review_text': rev_body,
                    'is_verified_viewer': True,
                    'is_edited': False
                }
            )
            movie_obj.update_average_rating()

        self.stdout.write(self.style.SUCCESS("Successfully seeded enhanced movie details, trailers, cast, and verified reviews!"))
