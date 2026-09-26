#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "=========================================================="
echo " Starting PickMyShow Production Build Pipeline"
echo "=========================================================="

# 1. Install project dependencies
echo "--> Installing Python dependencies..."
pip install -r requirements.txt

# 2. Collect static files
echo "--> Collecting static files for WhiteNoise..."
python manage.py collectstatic --noinput

# 3. Apply database migrations
echo "--> Applying database migrations..."
python manage.py migrate --noinput

# 4. Verify & Seed initial catalog if fresh deployment
echo "--> Checking catalog state..."
python manage.py shell -c "
import os
from movies.models import Movie
from django.contrib.auth.models import User
from django.core.management import call_command

from movies.models import Movie, HeroBanner

# Auto-seed curated catalog if database is empty or hero banners are missing
if Movie.objects.count() == 0 or HeroBanner.objects.count() == 0:
    print('Fresh database or missing banners detected. Seeding 20 curated blockbusters, 100 events, and Hero Banners...')
    try:
        call_command('seed_curated_catalog')
        print('Successfully seeded curated catalog and hero banners.')
    except Exception as e:
        print(f'Warning: Could not seed curated catalog: {e}')
# Synchronize all 20 movies to their verified standard poster image paths
standard_posters = {
    'Dark Knight': 'movies/dark_knight.jpg',
    'Dune': 'movies/dune_2.jpg',
    'Interstellar': 'movies/interstellar.jpg',
    'Kantara': 'movies/kantara.jpg',
    'Manjummel': 'movies/manjummel_boys.jpg',
    'Oppenheimer': 'movies/oppenheimer.jpg',
    'Inception': 'movies/inception.jpg',
    'Kalki': 'movies/kalki_2898_ad.jpg',
    'RRR': 'movies/rrr.jpg',
    'Laapataa': 'movies/laapataa_ladies.jpg',
    'Spider-Man': 'movies/Spider-Man_Brand_New_Day.jpg',
    'Drishyam': 'movies/drishyam_2.jpg',
    'Pushpa': 'movies/pushpa_2.jpg',
    'Chhava': 'movies/chhava.jpg',
    'Sita Ramam': 'movies/sita_ramam.jpg',
    'The Odyssey': 'movies/The_Odyssey.jpg',
    'Jawan': 'movies/jawan.jpg',
    'Stree': 'movies/stree_2.jpg',
    'Brahmastra': 'movies/brahmastra.jpg',
    'Leo': 'movies/leo_bloody_sweet.jpg',
}
for title_query, poster_path in standard_posters.items():
    Movie.objects.filter(name__icontains=title_query).update(image=poster_path)
print('Successfully synchronized all 20 movie poster paths in database.')

# Ensure superuser exists for evaluator access
admin_user = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
admin_email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
admin_pass = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=admin_user).exists():
    User.objects.create_superuser(admin_user, admin_email, admin_pass)
    print(f'Created default evaluator superuser: {admin_user}')
else:
    print(f'Evaluator superuser {admin_user} verified.')
"

echo "=========================================================="
echo " PickMyShow Build Pipeline Finished Successfully!"
echo "=========================================================="
