import csv
import os
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.core.files.base import ContentFile
from rest_framework import mixins, generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from analysis_module.forms import ProjectModelForm
from analysis_module.utils import format_file_size, process_dataset_file, generate_seaborn_chart
from .models import Project, DataSet, Column, Analysis
from .serializers import ProjectSerializer, ColumnSerializer, AnalysisSerializer


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


@method_decorator(login_required, name="dispatch")
class ProjectDetailView(DetailView):
    model = Project
    template_name = "processing.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        dataset = getattr(project, "dataset", None)

        context["dataset"] = dataset
        context["file_size_formatted"] = format_file_size(dataset.file_size) if dataset and dataset.file_size else "0 مگابایت"
        context["columns"] = dataset.columns.all() if dataset else []

        numeric_count = 0
        categorical_count = 0
        if dataset:
            for col in context["columns"]:
                if col.data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
                    numeric_count += 1
                else:
                    categorical_count += 1

        context["numeric_count"] = numeric_count
        context["categorical_count"] = categorical_count
        return context


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


class RunAnalysisAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        project = get_object_or_404(Project, pk=pk, user=request.user)
        dataset = getattr(project, "dataset", None)
        if not dataset or not dataset.file:
            return Response({"error": "دیتاستی برای این پروژه یافت نشد."}, status=status.HTTP_400_BAD_REQUEST)

        sample_percent = request.data.get("sample_percent", 100)
        try:
            sample_percent = int(sample_percent)
            if sample_percent < 1 or sample_percent > 100:
                sample_percent = 100
        except ValueError:
            sample_percent = 100

        file_path = dataset.file.path
        if not os.path.exists(file_path):
            return Response({"error": "فایل دیتاست یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        try:
            # خواندن CSV با پانداز
            try:
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            except Exception:
                df = pd.read_csv(file_path, encoding='utf-8', errors='replace')

            if sample_percent < 100 and len(df) > 0:
                df_sampled = df.sample(frac=sample_percent / 100.0)
            else:
                df_sampled = df

            columns = dataset.columns.all()

            for column in columns:
                # حذف تحلیل‌های قبلی این ستون
                column.analyses.all().delete()

                col_name = column.name
                if col_name not in df_sampled.columns:
                    continue

                series = df_sampled[col_name]
                mean_val = None
                median_val = None
                mode_val = None
                unique_counts = int(series.nunique())

                if column.data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
                    numeric_series = pd.to_numeric(series, errors='coerce').dropna()
                    if not numeric_series.empty:
                        mean_val = float(numeric_series.mean())
                        median_val = float(numeric_series.median())
                        mode_series = numeric_series.mode()
                        if not mode_series.empty:
                            mode_val = str(round(mode_series.iloc[0], 2))
                else:
                    mode_series = series.mode()
                    if not mode_series.empty:
                        mode_val = str(mode_series.iloc[0])

                # ساخت نمودار Seaborn
                chart_buf = generate_seaborn_chart(df_sampled, col_name, column.data_type)

                analysis = Analysis.objects.create(
                    column=column,
                    mean=mean_val,
                    median=median_val,
                    mode=mode_val,
                    value_counts=unique_counts
                )
                filename = f"chart_col_{column.id}_sample_{sample_percent}.png"
                analysis.visualization.save(filename, ContentFile(chart_buf.getvalue()), save=True)

            # بازگرداندن تمام ستون‌ها همراه با تحلیل ساخت جدید
            updated_columns = ColumnSerializer(columns, many=True, context={'request': request}).data
            return Response({
                "message": "تحلیل با موفقیت انجام شد.",
                "sample_percent": sample_percent,
                "sampled_records": len(df_sampled),
                "columns": updated_columns
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"خطا در پردازش تحلیل: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ColumnAnalysisAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        column = get_object_or_404(Column, pk=pk, dataset__project__user=request.user)
        analysis = column.analyses.last()
        if not analysis:
            return Response({"error": "تحلیلی برای این ستون ثبت نشده است."}, status=status.HTTP_44_NOT_FOUND)

        serializer = AnalysisSerializer(analysis, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

# endregion
