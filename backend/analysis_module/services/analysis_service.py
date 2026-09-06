import os
import pandas as pd
from django.core.files.base import ContentFile

from ..models import Project, Column, Analysis
from .dataset_service import DatasetService
from .profiling_service import ProfilingService
from .visualization_service import VisualizationService


class AnalysisService:
    @staticmethod
    def search_user_projects(user, query=""):
        return Project.objects.filter(user=user, name__icontains=query)

    @staticmethod
    def analyze_single_column(column: Column, sample_percent: int = 100):
        """
        اجرا و پردازش تحلیل یک ستون و ذخیره نمودار و آمار توصیفی در دیتابیس
        """
        dataset = column.dataset
        if not dataset or not dataset.file:
            return None, {"data": {"error": "دیتاستی یافت نشد."}, "status": 400}

        try:
            sample_percent = int(sample_percent)
            if sample_percent < 1 or sample_percent > 100:
                sample_percent = 100
        except ValueError:
            sample_percent = 100

        file_path = dataset.file.path
        if not os.path.exists(file_path):
            return None, {"data": {"error": "فایل دیتاست یافت نشد."}, "status": 404}

        try:
            df = DatasetService.load_dataframe(file_path)

            if sample_percent < 100 and len(df) > 0:
                df_sampled = df.sample(frac=sample_percent / 100.0)
            else:
                df_sampled = df

            col_name = column.name
            if col_name not in df_sampled.columns:
                return None, {"data": {"error": f"ستون {col_name} در فایل یافت نشد."}, "status": 400}

            # حذف تحلیل‌های قبلی این ستون
            column.analyses.all().delete()

            series = df_sampled[col_name]
            stats = ProfilingService.calculate_column_stats(series, column.data_type)

            # ساخت نمودار Seaborn
            chart_buf = VisualizationService.generate_seaborn_chart(df_sampled, col_name, column.data_type)

            analysis = Analysis.objects.create(
                column=column,
                mean=stats["mean"],
                median=stats["median"],
                mode=stats["mode"],
                value_counts=stats["value_counts"]
            )

            filename = f"chart_col_{column.id}_sample_{sample_percent}.png"
            analysis.visualization.save(filename, ContentFile(chart_buf.getvalue()), save=True)

            return {
                "analysis": analysis,
                "sampled_records": len(df_sampled)
            }, None

        except Exception as e:
            return None, {"data": {"error": f"خطا در تحلیل ستون: {str(e)}"}, "status": 500}

    @staticmethod
    def clear_project_analyses(project: Project):
        """
        پاکسازی تمام تحلیل‌های ثبت شده متعلق به یک پروژه
        """
        return Analysis.objects.filter(column__dataset__project=project).delete()

    @staticmethod
    def get_latest_column_analysis(column: Column):
        """
        دریافت آخرین تحلیل صورت گرفته برای یک ستون
        """
        return column.analyses.last()
