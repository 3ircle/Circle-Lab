from django.shortcuts import render, get_object_or_404
from django.http import StreamingHttpResponse
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from analysis_module.models import Project
from .models import ChatSession, ChatMessage
from .serializers import ChatSessionSerializer, ChatMessageSerializer
from .services import ChatService


@method_decorator(login_required, name="dispatch")
class ChatView(TemplateView):
    template_name = "chat.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        projects = Project.objects.filter(user=user)

        active_project_id = self.request.GET.get('project_id')
        active_project = None
        if active_project_id:
            active_project = projects.filter(id=active_project_id).first()
        if not active_project and projects.exists():
            active_project = projects.first()

        chat_sessions = ChatSession.objects.filter(user=user)
        if active_project:
            chat_sessions = chat_sessions.filter(project=active_project)

        context['projects'] = projects
        context['active_project'] = active_project
        context['chat_sessions'] = chat_sessions
        return context


class ChatSessionListAPIView(generics.ListAPIView):
    serializer_class = ChatSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ChatSession.objects.filter(user=self.request.user)
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset


class CreateChatSessionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        project_id = request.data.get('project_id')
        title = request.data.get('title', 'گفتگوی جدید')

        project = None
        if project_id:
            project = get_object_or_404(Project, id=project_id, user=request.user)

        session = ChatSession.objects.create(
            user=request.user,
            project=project,
            title=title
        )
        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatMessageListAPIView(generics.ListAPIView):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        session_id = self.kwargs.get('session_id')
        session = get_object_or_404(ChatSession, id=session_id, user=self.request.user)
        return session.messages.all()


class ChatMessageStreamAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(ChatSession, id=session_id, user=request.user)
        prompt = request.data.get('prompt', '').strip()

        if not prompt:
            return Response({'detail': 'متن پیام نمی‌تواند خالی باشد.'}, status=status.HTTP_400_BAD_REQUEST)

        # ذخیره پیام کاربر در دیتابیس
        ChatMessage.objects.create(
            session=session,
            sender='user',
            content=prompt
        )

        stream_gen = ChatService.stream_chat_response(session, prompt)
        response = StreamingHttpResponse(stream_gen, content_type='text/plain; charset=utf-8')
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache'
        return response
