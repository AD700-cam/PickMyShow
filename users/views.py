from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .forms import UserRegisterForm, UserUpdateForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from movies.models import Movie, Booking, Theater, HeroBanner, PaymentTransaction
from movies.views import get_personalized_recommendations

def home(request):
    selected_genre = request.GET.get('genre', '').strip()
    if selected_genre.lower() in ['', 'all']:
        selected_genre = None

    all_movies = list(Movie.objects.all().order_by('-rating', '-views_count'))
    if selected_genre:
        recommended_movies  = get_personalized_recommendations(request, limit=4, genre=selected_genre)
        now_showing_movies  = [m for m in all_movies if m.genre and m.genre.lower() == selected_genre.lower()][:20]
        if len(now_showing_movies) < 4:
            other_movies = [m for m in all_movies if not (m.genre and m.genre.lower() == selected_genre.lower())][:20 - len(now_showing_movies)]
            now_showing_movies = now_showing_movies + other_movies
    else:
        recommended_movies  = get_personalized_recommendations(request, limit=4)
        now_showing_movies  = all_movies[:20]

    hero_banners = HeroBanner.objects.filter(is_active=True).order_by('order')[:5]
    genres = [g[0] for g in Movie.GENRE_CHOICES]
    cities = [c[0] for c in Theater.CITY_CHOICES]
    return render(request, 'home.html', {
        'movies':             now_showing_movies,
        'all_movies':         all_movies,
        'recommended_movies': recommended_movies,
        'hero_banners':       hero_banners,
        'genres':             genres,
        'cities':             cities,
        'selected_genre':     selected_genre,
    })
def register(request):
    if request.method == 'POST':
        form=UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username=form.cleaned_data.get('username')
            password=form.cleaned_data.get('password1')
            user=authenticate(username=username,password=password)
            login(request,user)
            return redirect('profile')
    else:
        form=UserRegisterForm()
    return render(request,'users/register.html',{'form':form})

def login_view(request):
    if request.method == 'POST':
        form=AuthenticationForm(request,data=request.POST)
        if form.is_valid():
            user=form.get_user()
            login(request,user)
            return redirect('/')
    else:
        form=AuthenticationForm()
    return render(request,'users/login.html',{'form':form})

@login_required
def profile(request):
    user_bookings = (
        Booking.objects.filter(user=request.user)
        .select_related('movie', 'theater', 'seat')
        .order_by('-booked_at')
    )

    # Aggregate individual seat bookings by booking_id
    grouped_bookings = {}
    for b in user_bookings[:100]:
        bid = b.booking_id or f"LEGACY-{b.id}"
        if bid not in grouped_bookings:
            grouped_bookings[bid] = {
                'booking_id': b.booking_id,
                'payment_reference': b.payment_reference,
                'movie': b.movie,
                'theater': b.theater,
                'booked_at': b.booked_at,
                'payment_status': b.payment_status,
                'email_sent': b.email_sent,
                'seats': [b.seat.seat_number],
                'total_amount': b.total_price,
                'primary_booking': b,
            }
        else:
            grouped_bookings[bid]['seats'].append(b.seat.seat_number)
            grouped_bookings[bid]['total_amount'] += b.total_price

    booking_orders = list(grouped_bookings.values())
    user_transactions = (
        PaymentTransaction.objects.filter(user=request.user)
        .select_related('movie', 'theater')
        .order_by('-created_at')
    )
    total_orders_count = Booking.objects.filter(user=request.user).values('booking_id').distinct().count()

    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        if u_form.is_valid():
            u_form.save()
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)

    return render(request, 'users/profile.html', {
        'u_form': u_form,
        'bookings': user_bookings,
        'booking_orders': booking_orders,
        'total_orders_count': total_orders_count,
        'transactions': user_transactions,
    })

@login_required
def reset_password(request):
    if request.method == 'POST':
        form=PasswordChangeForm(user=request.user,data=request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form=PasswordChangeForm(user=request.user)
    return render(request,'users/reset_password.html',{'form':form})