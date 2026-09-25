from movies.models import Theater


def global_city_context(request):
    """
    Provides global city selection state and popular cities across all templates.
    Persists city selection across page navigation via user session.
    """
    city_param = request.GET.get('city')
    if city_param is not None:
        clean_city = city_param.strip()
        if clean_city.lower() in ['', 'all', 'none']:
            request.session.pop('selected_city', None)
            selected_city = None
        else:
            request.session['selected_city'] = clean_city
            selected_city = clean_city
    else:
        selected_city = request.session.get('selected_city')

    popular_cities = [
        {'name': 'Mumbai', 'icon': 'fa-building', 'tag': 'Western Hub'},
        {'name': 'Delhi-NCR', 'icon': 'fa-landmark', 'tag': 'Capital Region'},
        {'name': 'Bengaluru', 'icon': 'fa-laptop-code', 'tag': 'Silicon Valley'},
        {'name': 'Hyderabad', 'icon': 'fa-monument', 'tag': 'Cyber City'},
        {'name': 'Chennai', 'icon': 'fa-umbrella-beach', 'tag': 'South Cinema'},
        {'name': 'Kolkata', 'icon': 'fa-palette', 'tag': 'Cultural Hub'},
        {'name': 'Pune', 'icon': 'fa-graduation-cap', 'tag': 'Oxford of East'},
        {'name': 'Ahmedabad', 'icon': 'fa-sun', 'tag': 'Heritage City'},
    ]

    return {
        'selected_city': selected_city,
        'popular_cities': popular_cities,
        'all_cities': [c['name'] for c in popular_cities],
    }
