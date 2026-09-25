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

# Auto-seed curated catalog if database is empty
if Movie.objects.count() == 0:
    print('Fresh database detected. Seeding 20 curated blockbusters and 100 screening events...')
    try:
        call_command('seed_curated_catalog')
        print('Successfully seeded curated catalog.')
    except Exception as e:
        print(f'Warning: Could not seed curated catalog: {e}')
else:
    print(f'Database already contains {Movie.objects.count()} movies.')

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
