from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.urls import path


ADMIN_DOCS = (
    {
        'slug': 'backend-api',
        'title': '백엔드 API 명세',
        'description': '마이페이지에서 관리자 페이지로 이동한 백엔드 API 문서',
        'filename': 'pictable-backend-api-spec-v2.html',
        'type': 'html',
    },
    {
        'slug': 'backend-api-v2',
        'title': '백엔드 API 명세 v2',
        'description': '프론트 연동 기준 최신 API와 Django Admin CRUD 범위',
        'filename': 'pictable-backend-api-spec-v2.html',
        'type': 'html',
    },
    {
        'slug': 'frontend-spec-v2',
        'title': '프론트엔드 명세 v2',
        'description': 'Vue 3 SPA 구조, 런타임 흐름, 배포/테스트 기준',
        'filename': 'pictable-frontend-spec-v2.html',
        'type': 'html',
    },
    {
        'slug': 'user-flow-wireframe',
        'title': '사용자 플로우 와이어프레임',
        'description': '마이페이지에서 관리자 페이지로 이동한 사용자 흐름 문서',
        'filename': 'pictable-user-flow-wireframe-v2.html',
        'type': 'html',
    },
    {
        'slug': 'user-flow-wireframe-v2',
        'title': '사용자 플로우 와이어프레임 v2',
        'description': '사용자 흐름, OAuth, 추천, API 연동 와이어프레임',
        'filename': 'pictable-user-flow-wireframe-v2.html',
        'type': 'html',
    },
    {
        'slug': 'frontend-test-report-v2',
        'title': '프론트 기능 테스트 보고서 HTML',
        'description': 'Vitest, Playwright, Lighthouse 버전별/기기별 테스트 요약',
        'filename': 'pictable-frontend-test-report-v2.html',
        'type': 'html',
    },
    {
        'slug': 'frontend-test-report-v2-md',
        'title': '프론트 기능 테스트 보고서 MD',
        'description': '제출/복사용 Markdown 테스트 보고서 원문',
        'filename': 'pictable-frontend-test-report-v2.md',
        'type': 'markdown',
    },
)

ADMIN_DOCS_BY_SLUG = {doc['slug']: doc for doc in ADMIN_DOCS}
ADMIN_DOCS_DIR = settings.BASE_DIR / 'admin_docs'


def _doc_path(doc: dict[str, str]) -> Path:
    path = ADMIN_DOCS_DIR / doc['filename']
    try:
        path.relative_to(ADMIN_DOCS_DIR)
    except ValueError as exc:
        raise Http404('Invalid document path') from exc
    if not path.exists():
        raise Http404('Document not found')
    return path


def admin_docs_index(request):
    context = admin.site.each_context(request)
    context.update(
        {
            'title': '프로젝트 문서',
            'pictable_admin_docs': ADMIN_DOCS,
        }
    )
    return TemplateResponse(request, 'admin/pictable_docs_index.html', context)


def admin_doc_detail(request, slug):
    doc = ADMIN_DOCS_BY_SLUG.get(slug)
    if doc is None:
        raise Http404('Document not found')

    path = _doc_path(doc)
    if doc['type'] == 'html' and request.GET.get('raw') == '1':
        response = HttpResponse(path.read_text(encoding='utf-8'), content_type='text/html; charset=utf-8')
        response['X-Frame-Options'] = 'SAMEORIGIN'
        return response

    context = admin.site.each_context(request)
    context.update(
        {
            'title': doc['title'],
            'doc': doc,
            'doc_content': path.read_text(encoding='utf-8') if doc['type'] == 'markdown' else '',
            'raw_url': f'{request.path}?raw=1',
        }
    )
    return TemplateResponse(request, 'admin/pictable_doc_detail.html', context)


def _register_admin_docs():
    if getattr(admin.site, '_pictable_docs_registered', False):
        return

    original_get_urls = admin.site.get_urls

    def get_urls():
        custom_urls = [
            path('docs/', admin.site.admin_view(admin_docs_index), name='pictable_docs_index'),
            path('docs/<slug:slug>/', admin.site.admin_view(admin_doc_detail), name='pictable_doc_detail'),
        ]
        return custom_urls + original_get_urls()

    admin.site.get_urls = get_urls
    admin.site.index_template = 'admin/pictable_index.html'
    admin.site._pictable_docs_registered = True


_register_admin_docs()
