import csv
import os
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from rest_framework import mixins, generics, permissions
from analysis_module.forms import ProjectModelForm
from analysis_module.utils import format_file_size, process_dataset_file
from .models import Project, DataSet, Column, Analysis
from .serializers import ProjectSerializer


@method_decorator(login_required, name="dispatch")
class IndexView(TemplateView):
    template_name = "analysis_module/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context["projects"] = Project.objects.filter(user=user)
        context["projects_count"] = context["projects"].count()
        context["rows_count"] = (
            DataSet.objects.filter(project__user=user).aggregate(
                total=Sum("record_count")
            )["total"]
            or 0
        )

        total_bytes = (
            DataSet.objects.filter(project__user=user).aggregate(
                total=Sum("file_size")
            )["total"]
            or 0
        )
        context["file_size"] = format_file_size(total_bytes)

        return context


@method_decorator(login_required, name="dispatch")
class CreateProjectView(CreateView):
    model = Project
    template_name = "analysis_module/create_project.html"
    form_class = ProjectModelForm
    success_url = reverse_lazy("index-page")

    def form_valid(self, form):
        form.instance.user = self.request.user
        project = form.save()

        uploaded_file = self.request.FILES.get("file") or form.cleaned_data.get("file")
        if uploaded_file:
            dataset = DataSet.objects.create(
                project=project, file=uploaded_file, file_size=uploaded_file.size
            )
            # پردازش فایل دیتاست برای استخراج تعداد سطور، ستون‌ها و نوع داده
            process_dataset_file(dataset)

        return redirect(self.success_url)


# region Api Views

class SearchProjectsView(mixins.ListModelMixin, generics.GenericAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        query = self.request.GET.get("q", "")
        return Project.objects.filter(user=user, name__icontains=query)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

class DeleteProjectView(generics.DestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Project.objects.filter(user=user)
    
    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)





# endregion