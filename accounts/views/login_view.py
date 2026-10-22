import math
import time

from django.contrib.auth import authenticate
from django.core.cache import cache
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


# ---- Brute-force protection (login lockout) ----
# 5 galat attempts free. 6th galat attempt par lock lagta hai, aur uske baad har galat attempt par
# lock ka time badhta hai: 1 min -> 2 min -> 5 min -> 10 min -> 15 min (15 min par ruk jata hai).
# Sahi login hote hi sab reset. Lock server par hai, to page refresh karke ya API se bypass nahi hota.
MAX_FREE_ATTEMPTS = 5
LOCK_STEPS = [60, 120, 300, 600, 900]   # seconds
FAIL_WINDOW = 3600                       # 1 ghante tak koi galti na ho to counter reset


def _norm(username):
    # lowercase: "Admin" aur "admin" ko alag try karke bypass na kiya ja sake
    return str(username).strip().lower()[:150]


def _fail_key(u):
    return f'login_fail:{u}'


def _lock_key(u):
    return f'login_lock:{u}'


def _lock_remaining(u):
    until = cache.get(_lock_key(u))
    if not until:
        return 0
    return max(0, math.ceil(until - time.time()))


def _pretty(seconds):
    if seconds >= 60:
        m = math.ceil(seconds / 60)
        return f'{m} minute' + ('s' if m != 1 else '')
    return f'{seconds} second' + ('s' if seconds != 1 else '')


def _locked_response(seconds):
    resp = Response(
        {
            'error': f'Too many failed attempts. Try again in {_pretty(seconds)}.',
            'retry_after': seconds,
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    resp['Retry-After'] = str(seconds)
    return resp


class LoginView(APIView):

    
    """API endpoint for user login.
    Accepts 'username' and 'password', authenticates user,
    and returns an auth token.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response(
            {'message': 'Send a POST request with "username" and "password" to log in.'},
            status=status.HTTP_200_OK
        )

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        key = _norm(username)

        # Lock chal raha hai to password check hi nahi karte (sahi password par bhi nahi)
        remaining = _lock_remaining(key)
        if remaining:
            return _locked_response(remaining)

        user = authenticate(username=username, password=password)

        if not user:
            # Jo username exist nahi karta uska bhi same hisaab, taaki pata na chale kaun sa user hai
            fails = cache.get(_fail_key(key), 0) + 1
            cache.set(_fail_key(key), fails, FAIL_WINDOW)

            if fails > MAX_FREE_ATTEMPTS:
                step = min(fails - MAX_FREE_ATTEMPTS - 1, len(LOCK_STEPS) - 1)
                seconds = LOCK_STEPS[step]
                cache.set(_lock_key(key), time.time() + seconds, seconds)
                return _locked_response(seconds)

            return Response(
                {
                    'error': 'Invalid username or password.',
                    'attempts_left': MAX_FREE_ATTEMPTS - fails,
                },
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'User account is disabled.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Sahi login: failed attempts aur lock reset
        cache.delete(_fail_key(key))
        cache.delete(_lock_key(key))

        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                'message': 'Login successful.',
                'token': token.key,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                }
            },
            status=status.HTTP_200_OK
        )
