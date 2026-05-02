"""
Rate limiting utilities for API calls
"""

import time
from django.core.cache import cache
from functools import wraps
from django.contrib import messages


def rate_limit(max_calls: int = 10, time_window: int = 60):
    """
    Rate limiting decorator for view functions.
    
    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            # Create a unique key for this user
            if request.user.is_authenticated:
                user_id = request.user.id
            elif 'id' in request.session:
                user_id = request.session['id']
            else:
                user_id = request.META.get('REMOTE_ADDR', 'unknown')
            
            cache_key = f"rate_limit_{func.__name__}_{user_id}"
            
            # Get the request count from cache
            request_count = cache.get(cache_key, 0)
            
            if request_count >= max_calls:
                messages.error(
                    request,
                    f"⚠️ Too many requests. Please try again in {time_window} seconds."
                )
                # Return the same page with error message
                return func(request, *args, **kwargs)
            
            # Increment the counter
            cache.set(cache_key, request_count + 1, time_window)
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator
