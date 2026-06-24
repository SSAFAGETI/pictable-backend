import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from recipes.models import Recipe, RecipeLike, RecipeSave, Comment

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
        email='author@example.com',
        password='pass123!',
        nickname='작성자',
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email='other@example.com',
        password='pass123!',
        nickname='타유저',
    )


@pytest.fixture
def auth_client(client, user):
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


@pytest.fixture
def other_auth_client(other_user):
    c = APIClient()
    token = RefreshToken.for_user(other_user)
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return c


@pytest.fixture
def recipe(db, user):
    return Recipe.objects.create(
        author=user,
        title='김치찌개',
        description='맛있는 김치찌개',
        servings=2,
        cook_time=30,
        is_public=True,
        like_count=0,
        comment_count=0,
        save_count=0,
    )


@pytest.fixture
def comment(db, user, recipe):
    return Comment.objects.create(
        recipe=recipe,
        author=user,
        content='맛있겠다!',
    )


RECIPE_PAYLOAD = {
    'title': '된장찌개',
    'description': '구수한 된장찌개',
    'servings': 2,
    'cook_time': 20,
    'ingredients': [{'name': '된장', 'amount': '2큰술'}],
    'steps': [{'order': 1, 'description': '물을 끓인다'}],
}


# ─────────────────────────────────────────
# 레시피 목록 조회 / 생성
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestRecipeList:
    URL = '/api/recipes/'

    def test_list_unauthenticated(self, client, recipe):
        """비로그인도 목록 조회 가능 → 200"""
        res = client.get(self.URL)
        assert res.status_code == 200

    def test_list_returns_recipes(self, client, recipe):
        """레시피 목록에 생성한 레시피 포함"""
        res = client.get(self.URL)
        titles = [r['title'] for r in res.data]
        assert '김치찌개' in titles

    def test_create_authenticated(self, auth_client):
        """로그인 유저 레시피 생성 → 201"""
        res = auth_client.post(self.URL, RECIPE_PAYLOAD, format='json')
        assert res.status_code == 201
        assert res.data['title'] == '된장찌개'

    def test_create_unauthenticated(self, client):
        """비로그인 생성 시도 → 401"""
        res = client.post(self.URL, RECIPE_PAYLOAD, format='json')
        assert res.status_code == 401


# ─────────────────────────────────────────
# 레시피 상세 조회 / 수정 / 삭제
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestRecipeDetail:

    def url(self, pk):
        return f'/api/recipes/{pk}/'

    def test_get_detail(self, client, recipe):
        """레시피 상세 조회 → 200"""
        res = client.get(self.url(recipe.pk))
        assert res.status_code == 200
        assert res.data['title'] == '김치찌개'

    def test_get_not_found(self, client):
        """존재하지 않는 레시피 → 404"""
        res = client.get(self.url(99999))
        assert res.status_code == 404

    def test_patch_by_author(self, auth_client, recipe):
        """작성자 수정 → 200"""
        res = auth_client.patch(self.url(recipe.pk), {'title': '묵은지찌개'}, format='json')
        assert res.status_code == 200
        assert res.data['title'] == '묵은지찌개'

    def test_patch_by_other_user(self, other_auth_client, recipe):
        """타인 수정 시도 → 403"""
        res = other_auth_client.patch(self.url(recipe.pk), {'title': '해킹'}, format='json')
        assert res.status_code == 403

    def test_delete_by_author(self, auth_client, recipe):
        """작성자 삭제 → 204"""
        res = auth_client.delete(self.url(recipe.pk))
        assert res.status_code == 204
        assert not Recipe.objects.filter(pk=recipe.pk).exists()

    def test_delete_by_other_user(self, other_auth_client, recipe):
        """타인 삭제 시도 → 403"""
        res = other_auth_client.delete(self.url(recipe.pk))
        assert res.status_code == 403


# ─────────────────────────────────────────
# 좋아요 토글
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestRecipeLike:

    def url(self, pk):
        return f'/api/recipes/{pk}/like/'

    @patch('recipes.views.notify_like')
    def test_like_toggle_on(self, mock_notify, auth_client, recipe):
        """좋아요 → liked=True, like_count 증가"""
        res = auth_client.post(self.url(recipe.pk))
        assert res.status_code == 201
        assert res.data['liked'] is True
        assert res.data['like_count'] == 1
        mock_notify.assert_called_once()

    @patch('recipes.views.notify_like')
    def test_like_toggle_off(self, mock_notify, auth_client, recipe, user):
        """좋아요 취소 → liked=False, like_count 감소"""
        RecipeLike.objects.create(recipe=recipe, user=user)
        recipe.like_count = 1
        recipe.save()

        res = auth_client.post(self.url(recipe.pk))
        assert res.status_code == 200
        assert res.data['liked'] is False
        assert res.data['like_count'] == 0

    def test_like_unauthenticated(self, client, recipe):
        """비로그인 좋아요 → 401"""
        res = client.post(self.url(recipe.pk))
        assert res.status_code == 401


# ─────────────────────────────────────────
# 저장 토글
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestRecipeSave:

    def url(self, pk):
        return f'/api/recipes/{pk}/save/'

    def test_save_toggle_on(self, auth_client, recipe):
        """저장 → saved=True, save_count 증가"""
        res = auth_client.post(self.url(recipe.pk))
        assert res.status_code == 201
        assert res.data['saved'] is True
        assert res.data['save_count'] == 1

    def test_save_toggle_off(self, auth_client, recipe, user):
        """저장 취소 → saved=False, save_count 감소"""
        RecipeSave.objects.create(recipe=recipe, user=user)
        recipe.save_count = 1
        recipe.save()

        res = auth_client.post(self.url(recipe.pk))
        assert res.status_code == 200
        assert res.data['saved'] is False
        assert res.data['save_count'] == 0


# ─────────────────────────────────────────
# 댓글 목록 / 작성
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestCommentList:

    def url(self, pk):
        return f'/api/recipes/{pk}/comments/'

    def test_get_comments(self, client, recipe, comment):
        """댓글 목록 조회 → 200"""
        res = client.get(self.url(recipe.pk))
        assert res.status_code == 200
        assert len(res.data) == 1

    @patch('recipes.views.notify_comment')
    def test_post_comment(self, mock_notify, auth_client, recipe):
        """댓글 작성 → 201, comment_count 증가"""
        res = auth_client.post(self.url(recipe.pk), {'content': '맛있겠다!'})
        assert res.status_code == 201
        recipe.refresh_from_db()
        assert recipe.comment_count == 1
        mock_notify.assert_called_once()

    def test_post_comment_unauthenticated(self, client, recipe):
        """비로그인 댓글 작성 → 401"""
        res = client.post(self.url(recipe.pk), {'content': '맛있겠다!'})
        assert res.status_code == 401


# ─────────────────────────────────────────
# 댓글 수정 / 삭제
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestCommentDetail:

    def url(self, pk, comment_pk):
        return f'/api/recipes/{pk}/comments/{comment_pk}/'

    def test_patch_by_author(self, auth_client, recipe, comment):
        """작성자 댓글 수정 → 200"""
        res = auth_client.patch(self.url(recipe.pk, comment.pk), {'content': '수정된 댓글'})
        assert res.status_code == 200

    def test_patch_by_other(self, other_auth_client, recipe, comment):
        """타인 댓글 수정 → 403"""
        res = other_auth_client.patch(self.url(recipe.pk, comment.pk), {'content': '해킹'})
        assert res.status_code == 403

    def test_delete_soft(self, auth_client, recipe, comment):
        """댓글 소프트 삭제 → 204, deleted_at 설정, comment_count 감소"""
        recipe.comment_count = 1
        recipe.save()

        res = auth_client.delete(self.url(recipe.pk, comment.pk))
        assert res.status_code == 204
        comment.refresh_from_db()
        assert comment.deleted_at is not None
        recipe.refresh_from_db()
        assert recipe.comment_count == 0


# ─────────────────────────────────────────
# 답글 작성
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestReplyCreate:

    def url(self, pk, comment_pk):
        return f'/api/recipes/{pk}/comments/{comment_pk}/replies/'

    @patch('recipes.views.notify_reply')
    def test_create_reply(self, mock_notify, auth_client, recipe, comment):
        """답글 작성 → 201"""
        res = auth_client.post(self.url(recipe.pk, comment.pk), {'content': '동의해요!'})
        assert res.status_code == 201
        mock_notify.assert_called_once()

    def test_reply_on_nonexistent_comment(self, auth_client, recipe):
        """존재하지 않는 댓글에 답글 → 404"""
        res = auth_client.post(self.url(recipe.pk, 99999), {'content': '답글'})
        assert res.status_code == 404


# ─────────────────────────────────────────
# 레시피 추천
# ─────────────────────────────────────────

@pytest.mark.django_db
class TestRecommendRecipes:
    URL = '/api/recipes/recommendations/'

    @patch('recipes.views.get_recommendations')
    @patch('recipes.views.normalize_ingredients')
    def test_recommend_success(self, mock_normalize, mock_recommend, auth_client):
        """정상 추천 요청 → 200, can_make/almost 반환"""
        mock_normalize.return_value = ['돼지고기', '마늘']
        mock_recommend.return_value = (
            [{'recipe_id': 1, 'title': '제육볶음', 'missing_count': 0}],
            [{'recipe_id': 2, 'title': '마늘볶음', 'missing_count': 1}],
        )

        res = auth_client.get(self.URL, {'ingredients': '돼지고기,마늘'})
        assert res.status_code == 200
        assert 'can_make' in res.data
        assert 'almost' in res.data
        assert len(res.data['can_make']) == 1

    def test_recommend_no_ingredients(self, auth_client):
        """ingredients 없이 요청 → 400"""
        res = auth_client.get(self.URL)
        assert res.status_code == 400

    def test_recommend_too_many_ingredients(self, auth_client):
        """51개 재료 → 400"""
        ingredients = ','.join([f'재료{i}' for i in range(51)])
        res = auth_client.get(self.URL, {'ingredients': ingredients})
        assert res.status_code == 400

    def test_recommend_unauthenticated(self, client):
        """비로그인 추천 요청 → 401"""
        res = client.get(self.URL, {'ingredients': '돼지고기'})
        assert res.status_code == 401