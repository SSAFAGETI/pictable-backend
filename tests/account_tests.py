import pytest
from unittest.mock import patch, MagicMock
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


# ─────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────

@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123!',
        nickname='테스터',
    )


@pytest.fixture
def auth_client(client, user):
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# ─────────────────────────────────────────
# 회원가입
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestSignup:
    URL = '/api/auth/signup/'

    @patch('accounts.views.notify_welcome')
    def test_signup_success(self, mock_notify, client):
        """정상 회원가입 → 201, 이메일/닉네임 반환"""
        data = {
            'email': 'new@example.com',
            'password': 'newpass123!',
            'nickname': '새유저',
        }
        res = client.post(self.URL, data)

        assert res.status_code == 201
        assert res.data['email'] == 'new@example.com'
        assert res.data['nickname'] == '새유저'
        assert User.objects.filter(email='new@example.com').exists()
        mock_notify.assert_called_once()

    @patch('accounts.views.notify_welcome')
    def test_signup_duplicate_email(self, mock_notify, client, user):
        """중복 이메일 → 400"""
        data = {
            'email': 'test@example.com',
            'password': 'newpass123!',
            'nickname': '중복유저',
        }
        res = client.post(self.URL, data)

        assert res.status_code == 400

    @patch('accounts.views.notify_welcome')
    def test_signup_missing_field(self, mock_notify, client):
        """필수 필드 누락 → 400"""
        res = client.post(self.URL, {'email': 'missing@example.com'})

        assert res.status_code == 400


# ─────────────────────────────────────────
# 로그인
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    URL = '/api/auth/login/'

    def test_login_success(self, client, user):
        """정상 로그인 → 200, access/refresh 토큰 반환"""
        res = client.post(self.URL, {
            'email': 'test@example.com',
            'password': 'testpass123!',
        })

        assert res.status_code == 200
        assert 'access' in res.data
        assert 'refresh' in res.data
        assert res.data['email'] == 'test@example.com'

    def test_login_wrong_password(self, client, user):
        """틀린 비밀번호 → 400"""
        res = client.post(self.URL, {
            'email': 'test@example.com',
            'password': 'wrongpass!',
        })

        assert res.status_code == 400

    def test_login_nonexistent_user(self, client):
        """존재하지 않는 유저 → 400"""
        res = client.post(self.URL, {
            'email': 'ghost@example.com',
            'password': 'somepass123!',
        })

        assert res.status_code == 400


# ─────────────────────────────────────────
# 로그아웃
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestLogout:
    URL = '/api/auth/logout/'

    def test_logout_success(self, auth_client, user):
        """유효한 refresh 토큰으로 로그아웃 → 200"""
        refresh = str(RefreshToken.for_user(user))
        res = auth_client.post(self.URL, {'refresh': refresh})

        assert res.status_code == 200
        assert res.data['message'] == '로그아웃 되었습니다.'

    def test_logout_invalid_token(self, auth_client):
        """유효하지 않은 refresh 토큰 → 400"""
        res = auth_client.post(self.URL, {'refresh': 'invalid.token.here'})

        assert res.status_code == 400


# ─────────────────────────────────────────
# 토큰 재발급
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:
    URL = '/api/auth/refresh/'

    def test_refresh_success(self, client, user):
        """유효한 refresh 토큰 → 200, 새 access 토큰 반환"""
        refresh = str(RefreshToken.for_user(user))
        res = client.post(self.URL, {'refresh': refresh})

        assert res.status_code == 200
        assert 'access' in res.data

    def test_refresh_invalid_token(self, client):
        """유효하지 않은 refresh 토큰 → 401"""
        res = client.post(self.URL, {'refresh': 'bad.token'})

        assert res.status_code == 401


# ─────────────────────────────────────────
# 구글 로그인 (외부 API mocking)
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestGoogleLogin:
    URL = '/api/auth/google/'

    def _mock_google(self, mock_post, mock_get, email='google@example.com', name='구글유저'):
        """구글 OAuth 외부 API 응답 mock 헬퍼"""
        mock_post.return_value = MagicMock(
            json=lambda: {'access_token': 'fake_access_token'}
        )
        mock_get.return_value = MagicMock(
            json=lambda: {
                'email': email,
                'name': name,
                'id': 'google_uid_123',
            }
        )

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_login_new_user(self, mock_post, mock_get, client):
        """신규 구글 유저 → 201 created=True, 토큰 반환"""
        self._mock_google(mock_post, mock_get)

        res = client.post(self.URL, {'code': 'fake_code'})

        assert res.status_code == 200
        assert 'access' in res.data
        assert res.data['created'] is True
        assert User.objects.filter(email='google@example.com').exists()

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_login_existing_user(self, mock_post, mock_get, client, db):
        """기존 구글 유저 재로그인 → created=False"""
        User.objects.create_user(
            email='google@example.com',
            nickname='기존유저',
            provider='google',
        )
        self._mock_google(mock_post, mock_get)

        res = client.post(self.URL, {'code': 'fake_code'})

        assert res.status_code == 200
        assert res.data['created'] is False

    def test_google_login_no_code(self, client):
        """code 없이 요청 → 400"""
        res = client.post(self.URL, {})

        assert res.status_code == 400

    @patch('accounts.views.requests.get')
    @patch('accounts.views.requests.post')
    def test_google_login_token_error(self, mock_post, mock_get, client):
        """구글 토큰 요청 실패 → 400"""
        mock_post.return_value = MagicMock(
            json=lambda: {'error': 'invalid_grant'}
        )

        res = client.post(self.URL, {'code': 'bad_code'})

        assert res.status_code == 400