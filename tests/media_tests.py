import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.files.uploadedfile import SimpleUploadedFile
from medias.models import MediaFile, IngredientDetectionJob, IngredientDetectionItem

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
        email='uploader@example.com',
        password='pass123!',
        nickname='업로더',
    )


@pytest.fixture
def auth_client(client, user):
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def image_file():
    """테스트용 가짜 이미지 파일"""
    return SimpleUploadedFile(
        name='test.jpg',
        content=b'\xff\xd8\xff\xe0' + b'\x00' * 100,  # 최소 JPEG 헤더
        content_type='image/jpeg',
    )


@pytest.fixture
def media_file(db, user):
    return MediaFile.objects.create(
        uploader_user=user,
        url='/media/general/test.jpg',
        original_name='test.jpg',
        mime_type='image/jpeg',
        purpose='general',
        size_bytes=1024,
    )


@pytest.fixture
def detection_job(db, user, media_file):
    return IngredientDetectionJob.objects.create(
        user=user,
        media_file=media_file,
        status='completed',
    )


@pytest.fixture
def detection_items(db, detection_job):
    IngredientDetectionItem.objects.create(
        detection_job=detection_job,
        detected_name='돼지고기',
        confidence=0.95,
    )
    IngredientDetectionItem.objects.create(
        detection_job=detection_job,
        detected_name='마늘',
        confidence=0.88,
    )


# ─────────────────────────────────────────
# 미디어 업로드
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestMediaUpload:
    URL = '/api/media/upload/'

    @patch('medias.views.os.makedirs')
    @patch('builtins.open', create=True)
    def test_upload_success(self, mock_open, mock_makedirs, auth_client, image_file):
        """일반 파일 업로드 → 201, id/url 반환"""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.write = MagicMock()

        res = auth_client.post(self.URL, {'file': image_file, 'purpose': 'general'})

        assert res.status_code == 201
        assert 'id' in res.data
        assert 'url' in res.data
        assert 'detection_job_id' not in res.data

    def test_upload_no_file(self, auth_client):
        """파일 없이 요청 → 400"""
        res = auth_client.post(self.URL, {'purpose': 'general'})
        assert res.status_code == 400

    def test_upload_unauthenticated(self, client, image_file):
        """비로그인 업로드 → 401"""
        res = client.post(self.URL, {'file': image_file})
        assert res.status_code == 401

    @patch('medias.views.run_ingredient_detection')
    @patch('medias.views.os.makedirs')
    @patch('builtins.open', create=True)
    def test_upload_ingredient_detection(self, mock_open, mock_makedirs, mock_detect, auth_client):
        """ingredient_detection purpose → detection_job_id 포함, run_ingredient_detection 호출"""
        mock_open.return_value.__enter__ = lambda s: s
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_open.return_value.write = MagicMock()

        image = SimpleUploadedFile(
            name='fridge.jpg',
            content=b'\xff\xd8\xff\xe0' + b'\x00' * 100,
            content_type='image/jpeg',
        )
        res = auth_client.post(self.URL, {'file': image, 'purpose': 'ingredient_detection'})

        assert res.status_code == 201
        assert 'detection_job_id' in res.data
        mock_detect.assert_called_once()


# ─────────────────────────────────────────
# 미디어 상세 조회
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestMediaDetail:

    def url(self, pk):
        return f'/api/media/{pk}/'

    def test_get_detail(self, client, media_file):
        """미디어 상세 조회 → 200, id/url 반환"""
        res = client.get(self.url(media_file.pk))
        assert res.status_code == 200
        assert res.data['id'] == media_file.pk
        assert 'url' in res.data

    def test_get_not_found(self, client):
        """존재하지 않는 미디어 → 404"""
        res = client.get(self.url(99999))
        assert res.status_code == 404

    def test_get_unauthenticated_allowed(self, client, media_file):
        """비로그인도 미디어 조회 가능"""
        res = client.get(self.url(media_file.pk))
        assert res.status_code == 200


# ─────────────────────────────────────────
# 재료 감지 결과 조회
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestDetectionResult:

    def url(self, job_id):
        return f'/api/media/detection/{job_id}/'

    def test_get_result_completed(self, auth_client, detection_job, detection_items):
        """완료된 job 조회 → 200, status/items 반환"""
        res = auth_client.get(self.url(detection_job.pk))
        assert res.status_code == 200
        assert res.data['status'] == 'completed'
        assert len(res.data['items']) == 2
        names = [item['name'] for item in res.data['items']]
        assert '돼지고기' in names
        assert '마늘' in names

    def test_get_result_pending(self, auth_client, user, media_file):
        """대기 중인 job → status=pending, items 비어있음"""
        job = IngredientDetectionJob.objects.create(
            user=user,
            media_file=media_file,
            status='pending',
        )
        res = auth_client.get(self.url(job.pk))
        assert res.status_code == 200
        assert res.data['status'] == 'pending'
        assert res.data['items'] == []

    def test_get_result_other_user(self, other_auth_client, detection_job):
        """타인의 job 조회 → 404"""
        res = other_auth_client.get(self.url(detection_job.pk))
        assert res.status_code == 404

    def test_get_result_unauthenticated(self, client, detection_job):
        """비로그인 → 401"""
        res = client.get(self.url(detection_job.pk))
        assert res.status_code == 401

    def test_get_result_not_found(self, auth_client):
        """존재하지 않는 job → 404"""
        res = auth_client.get(self.url(99999))
        assert res.status_code == 404


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email='other@example.com',
        password='pass123!',
        nickname='타유저',
    )


@pytest.fixture
def other_auth_client(client, other_user):
    c = APIClient()
    token = RefreshToken.for_user(other_user)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return c