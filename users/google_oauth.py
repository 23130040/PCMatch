import json
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class GoogleOAuthError(Exception):
    pass


def google_authorization_url(*, state, redirect_uri):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise GoogleOAuthError('Đăng nhập Google chưa được cấu hình.')
    parameters = urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
    })
    return f'https://accounts.google.com/o/oauth2/v2/auth?{parameters}'


def _request_json(request):
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError) as error:
        raise GoogleOAuthError('Không thể kết nối dịch vụ Google. Vui lòng thử lại.') from error
    if len(body) > 1024 * 1024:
        raise GoogleOAuthError('Phản hồi từ Google vượt quá giới hạn cho phép.')
    try:
        payload = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GoogleOAuthError('Phản hồi từ Google không hợp lệ.') from error
    if not isinstance(payload, dict) or payload.get('error'):
        raise GoogleOAuthError('Google không cấp quyền đăng nhập. Vui lòng thử lại.')
    return payload


def get_google_identity(*, code, redirect_uri):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise GoogleOAuthError('Đăng nhập Google chưa được cấu hình.')

    token_request = Request(
        'https://oauth2.googleapis.com/token',
        data=urlencode({
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': redirect_uri,
        }).encode('utf-8'),
        headers={
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'PCMatch/1.0',
        },
        method='POST',
    )
    token_payload = _request_json(token_request)
    access_token = token_payload.get('access_token')
    if not isinstance(access_token, str) or not access_token:
        raise GoogleOAuthError('Google không trả về mã truy cập hợp lệ.')

    userinfo_request = Request(
        'https://openidconnect.googleapis.com/v1/userinfo',
        headers={
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
            'User-Agent': 'PCMatch/1.0',
        },
    )
    return _request_json(userinfo_request)
