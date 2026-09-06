from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework import mixins, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from analysis_module.forms import ProjectModelForm
from .models import Project, DataSet, Column
from .serializers import ProjectSerializer, DataSetSerializer, ColumnSerializer, AnalysisSerializer
from .services import DatasetService, AnalysisService


@method_decorator(login_required, name="dispatch")
class IndexView(TemplateView):
    template_name = "analysis_module/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = DatasetService.get_user_dashboard_stats(self.request.user)
        context.update(stats)
        return context


@method_decorator(login_required, name="dispatch")
class CreateProjectView(CreateView):
    model = Project
    template_name = "analysis_module/create_project.html"
    form_class = ProjectModelForm
    success_url = reverse_lazy("index-page")

    def form_valid(self, form):
        uploaded_file = self.request.FILES.get("file") or form.cleaned_data.get("file")
        DatasetService.create_project_with_dataset(
            user=self.request.user,
            form=form,
            uploaded_file=uploaded_file
        )
        return redirect(self.success_url)


@method_decorator(login_required, name="dispatch")
class ProjectDetailView(DetailView):
    model = Project
    template_name = "processing.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        detail_context = DatasetService.get_project_detail_context(self.object)
        context.update(detail_context)
        return context


# region Api Views

class SearchProjectsView(mixins.ListModelMixin, generics.GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.GET.get("q", "")
        return AnalysisService.search_user_projects(self.request.user, query)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class DeleteProjectView(generics.DestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class AnalyzeSingleColumnAPIView(APIView):
    """
    تحلیل تک‌ستون به صورت جداگانه (زنده / Streaming)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        column = get_object_or_404(Column, pk=pk, dataset__project__user=request.user)
        sample_percent = request.data.get("sample_percent", 100)

        result, error = AnalysisService.analyze_single_column(column, sample_percent)
        if error:
            return Response(error["data"], status=error["status"])

        column_data = ColumnSerializer(column, context={'request': request}).data
        return Response({
            "column": column_data,
            "sampled_records": result["sampled_records"]
        }, status=status.HTTP_200_OK)


class ClearProjectAnalysesAPIView(APIView):
    """
    پاکسازی تمام تحلیل‌های قبلی پروژه پیش از شروع تحلیل زنده جدید
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        AnalysisService.clear_project_analyses(project)
        return Response({"message": "تمام تحلیل‌های قبلی پاکسازی شدند."}, status=status.HTTP_200_OK)


class ColumnAnalysisAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        column = get_object_or_404(Column, pk=pk, dataset__project__user=request.user)
        analysis = AnalysisService.get_latest_column_analysis(column)
        if not analysis:
            return Response({"error": "تحلیلی برای این ستون ثبت نشده است."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AnalysisSerializer(analysis, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class DataSetStatusAPIView(APIView):
    """
    استعلام وضعیت پردازش پس‌زمینه دیتاست (برای Polling فرانت‌اند)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        dataset = get_object_or_404(DataSet, pk=pk, project__user=request.user)
        serializer = DataSetSerializer(dataset, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

# endregion
