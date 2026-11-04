import json
import re
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class FacebookOAuthError(Exception):
    pass


def facebook_graph_version():
    version = settings.FACEBOOK_GRAPH_VERSION
    if not re.fullmatch(r'v\d+\.\d+', version):
        raise FacebookOAuthError('Cấu hình phiên bản Facebook Graph API không hợp lệ.')
    return version


def facebook_authorization_url(*, state, redirect_uri):
    if not settings.FACEBOOK_APP_ID or not settings.FACEBOOK_APP_SECRET:
        raise FacebookOAuthError('Đăng nhập Facebook chưa được cấu hình.')
    version = facebook_graph_version()
    parameters = urlencode({
        'client_id': settings.FACEBOOK_APP_ID,
        'redirect_uri': redirect_uri,
        'state': state,
        'scope': 'email,public_profile',
        'response_type': 'code',
    })
    return f'https://www.facebook.com/{version}/dialog/oauth?{parameters}'


def _request_json(url, *, access_token=None):
    headers = {'Accept': 'application/json', 'User-Agent': 'PCMatch/1.0'}
    if access_token:
        headers['Authorization'] = f'Bearer {access_token}'
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            body = response.read(1024 * 1024 + 1)
    except (HTTPError, URLError, HTTPException, TimeoutError, OSError) as error:
        raise FacebookOAuthError('Không thể kết nối dịch vụ Facebook. Vui lòng thử lại.') from error
    if len(body) > 1024 * 1024:
        raise FacebookOAuthError('Phản hồi từ Facebook vượt quá giới hạn cho phép.')
    try:
        payload = json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FacebookOAuthError('Phản hồi từ Facebook không hợp lệ.') from error
    if not isinstance(payload, dict):
        raise FacebookOAuthError('Phản hồi từ Facebook không hợp lệ.')
    if payload.get('error'):
        raise FacebookOAuthError('Facebook không cấp quyền đăng nhập. Vui lòng thử lại.')
    return payload


def get_facebook_identity(*, code, redirect_uri):
    if not settings.FACEBOOK_APP_ID or not settings.FACEBOOK_APP_SECRET:
        raise FacebookOAuthError('Đăng nhập Facebook chưa được cấu hình.')
    version = facebook_graph_version()
    token_url = 'https://graph.facebook.com/{}/oauth/access_token?{}'.format(
        version,
        urlencode({
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'redirect_uri': redirect_uri,
            'code': code,
        }),
    )
    token_payload = _request_json(token_url)
    access_token = token_payload.get('access_token')
    if not isinstance(access_token, str) or not access_token:
        raise FacebookOAuthError('Facebook không trả về mã truy cập hợp lệ.')

    identity_url = 'https://graph.facebook.com/{}/me?{}'.format(
        version,
        urlencode({'fields': 'id,name,email'}),
    )
    identity = _request_json(identity_url, access_token=access_token)
    if not isinstance(identity.get('id'), str) or not identity['id']:
        raise FacebookOAuthError('Không xác định được tài khoản Facebook.')
    return identity
