# blog/views.py
#
# =============================================================================
#  SMART CACHE LAYER — GUIDED ACTIVITY
#  Advanced Python Programming | ALU BSE
# =============================================================================
#
#  This file contains three API views. Your job is to add caching to each one.
#  Read each TODO carefully — they build on each other.
#
#  Run the timing script first (docs/ACTIVITY.md → Level 1) to see
#  how slow the uncached responses are before you begin.
# =============================================================================

import time
import logging

from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status

from .models import Post
from .serializers import PostSerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LEVEL 2 — Shared Cache (Public Data)
# ---------------------------------------------------------------------------

class PostListView(APIView):
    """
    GET  /api/posts/       — Returns all published posts.
    POST /api/posts/       — Creates a new post (authenticated users only).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get(self, request):
        params = request.query_params.urlencode()
        cache_key = f"posts:list:{params}" if params else "posts:list"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        posts = Post.objects.filter(status=Post.STATUS_PUBLISHED).select_related("author")
        serializer = PostSerializer(posts, many=True)
        data = serializer.data
        cache.set(cache_key, data, timeout=300)
        return Response(data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            # A newly published post changes the shared list response.
            cache.delete("posts:list")
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# LEVEL 2 (continued) — Single Post Cache
# ---------------------------------------------------------------------------

class PostDetailView(APIView):
    """
    GET /api/posts/<post_id>/ — Returns a single published post.
    """

    permission_classes = [AllowAny]

    def get(self, request, post_id: int):
        cache_key = f"posts:detail:{post_id}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        try:
            post = Post.objects.select_related("author").get(
                id=post_id, status=Post.STATUS_PUBLISHED
            )
        except Post.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PostSerializer(post)
        data = serializer.data
        cache.set(cache_key, data, timeout=600)
        return Response(data)


# ---------------------------------------------------------------------------
# LEVEL 3 — User-Isolated Cache (Personal Data)
# ---------------------------------------------------------------------------

class MyDraftsView(APIView):
    """
    GET /api/posts/my-drafts/ — Returns draft posts for the logged-in user only.

    !! SECURITY CRITICAL !!
    This endpoint returns private data. Every student must ensure
    that User A can never see User B's drafts under any circumstances.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # A generic key would return the first user's private drafts to every
        # later user until expiry, so the authenticated user's ID is required.
        cache_key = f"posts:my-drafts:{request.user.pk}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        drafts = Post.objects.filter(
            author=request.user,
            status=Post.STATUS_DRAFT
        ).select_related("author")

        serializer = PostSerializer(drafts, many=True)
        data = serializer.data
        cache.set(cache_key, data, timeout=120)
        return Response(data)


# ---------------------------------------------------------------------------
# BONUS — Deliberately Broken View (Level 3 Bug-Spotting)
# ---------------------------------------------------------------------------

class BrokenDraftsView(APIView):
    """
    GET /api/posts/broken-drafts/

    This view has a critical security bug.
    Your task: read the code, find the bug, and explain it in the activity sheet.
    DO NOT fix the code here — write your answer in docs/ACTIVITY.md.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # !! BUG: find it, name it, explain the real-world impact !!
        data = cache.get("my-drafts")
        if data is None:
            drafts = Post.objects.filter(
                author=request.user,
                status=Post.STATUS_DRAFT
            ).select_related("author")
            serializer = PostSerializer(drafts, many=True)
            data = serializer.data
            cache.set("my-drafts", data, timeout=120)
        return Response(data)
