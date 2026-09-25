from django.urls import path
from . import views

urlpatterns = [
    path('', views.movie_list, name='movie_list'),
    path('<int:movie_id>/', views.movie_detail, name='movie_detail'),
    path('<int:movie_id>/theaters', views.theater_list, name='theater_list'),
    path('<int:movie_id>/review/', views.submit_review, name='submit_review'),
    path('review/<int:review_id>/delete/', views.delete_review, name='delete_review'),
    path('review/<int:review_id>/report/', views.report_review, name='report_review'),
    path('theater/<int:theater_id>/seats/book/', views.book_seats, name='book_seats'),
    path('theater/<int:theater_id>/seats/availability/', views.seat_availability_api, name='seat_availability_api'),
    path('theater/<int:theater_id>/seats/reserve/', views.reserve_seats_api, name='reserve_seats_api'),
    path('theater/<int:theater_id>/seats/modify/', views.modify_reservation_api, name='modify_reservation_api'),
    path('theater/<int:theater_id>/seats/release/', views.release_reservation_api, name='release_reservation_api'),
    path('theater/<int:theater_id>/payment/initiate/', views.initiate_payment, name='initiate_payment'),
    path('theater/<int:theater_id>/payment/verify/', views.verify_payment, name='verify_payment'),
    path('theater/<int:theater_id>/payment/cancel/', views.cancel_payment, name='cancel_payment'),
    path('payment/retry/<int:transaction_id>/', views.retry_payment, name='retry_payment'),
    path('payment/webhook/', views.payment_webhook, name='payment_webhook'),
    path('payment/success/<str:booking_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/<int:transaction_id>/', views.payment_failed, name='payment_failed'),
    path('ticket/<str:booking_id>/download/', views.download_ticket, name='download_ticket'),
    path('ticket/<str:booking_id>/view/', views.view_ticket, name='view_ticket'),
    path('ticket/<str:booking_id>/resend-email/', views.resend_ticket_email, name='resend_ticket_email'),
    # Task 5: Admin Dashboard & Business Intelligence CSV Exports
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/export/revenue/', views.export_revenue_csv, name='export_revenue_csv'),
    path('admin-dashboard/export/theaters/', views.export_theaters_csv, name='export_theaters_csv'),
    path('admin-dashboard/export/movies/', views.export_movies_csv, name='export_movies_csv'),
    path('admin-dashboard/export/bookings/', views.export_bookings_csv, name='export_bookings_csv'),
]