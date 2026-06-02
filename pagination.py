from rest_framework.pagination import CursorPagination
from rest_framework.response import Response

class FeedCursorPagination(CursorPagination):
    page_size = 12
    page_size_query_param = 'page_size'
    max_page_size = 50
    ordering = ('-created_at', '-id')

    def get_paginated_response(self, data):
        return Response({
            'results': data,
            'next_cursor': self.get_next_link(),
            'has_next': self.get_next_link() is not None,
        })