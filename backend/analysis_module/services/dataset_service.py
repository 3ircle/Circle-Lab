import csv
import os
import pandas as pd
from django.db.models import Sum
from django.core.files.base import ContentFile

from ..models import Project, DataSet, Column
from .profiling_service import ProfilingService
from .visualization_service import VisualizationService


class DatasetService:
    @staticmethod
    def format_file_size(size_in_bytes):
        if not size_in_bytes:
            return "0 مگابایت"
        size_in_mb = size_in_bytes / (1024 * 1024)
        if size_in_mb >= 1024:
            size_in_gb = size_in_mb / 1024
            return f"{size_in_gb:.2f} گیگابایت"
        return f"{size_in_mb:.2f} مگابایت"

    @staticmethod
    def load_dataframe(file_path: str) -> pd.DataFrame:
        """
        لودر متمرکز انواع فرمت‌های دیتاست (.csv, .txt, .xlsx, .xls, .parquet)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"فایل در مسیر {file_path} یافت نشد.")

        ext = os.path.splitext(file_path)[1].lower()

        if ext in ['.csv', '.txt']:
            try:
                encoding = "utf-8-sig"
                try:
                    with open(file_path, "r", encoding=encoding) as f:
                        f.readline()
                except UnicodeDecodeError:
                    encoding = "utf-8"

                with open(file_path, "r", encoding=encoding, errors="replace") as f:
                    sample = f.read(4096)

                delimiter = ","
                if sample:
                    if sample.count(";") > sample.count(","):
                        delimiter = ";"
                    elif sample.count("\t") > sample.count(","):
                        delimiter = "\t"

                return pd.read_csv(file_path, encoding=encoding, encoding_errors="replace", delimiter=delimiter)
            except Exception:
                return pd.read_csv(file_path, encoding="utf-8", encoding_errors="replace")

        elif ext in ['.xlsx', '.xls']:
            return pd.read_excel(file_path)

        elif ext == '.parquet':
            return pd.read_parquet(file_path)

        else:
            raise ValueError(f"فرمت فایل {ext} پشتیبانی نمی‌شود.")

    @staticmethod
    def get_user_dashboard_stats(user):
        projects = Project.objects.filter(user=user)
        projects_count = projects.count()
        rows_count = (
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
        file_size = DatasetService.format_file_size(total_bytes)

        return {
            "projects": projects,
            "projects_count": projects_count,
            "rows_count": rows_count,
            "file_size": file_size,
        }

    @staticmethod
    def create_project_with_dataset(user, form, uploaded_file):
        """
        ساخت پروژه و دیتاست در حالت در انتظار پردازش (Pending) و ارسال فرایند به Celery Async Task
        """
        form.instance.user = user
        project = form.save()

        if uploaded_file:
            dataset = DataSet.objects.create(
                project=project,
                file=uploaded_file,
                file_size=uploaded_file.size,
                status=DataSet.STATUS_CHOICES[0][0] # 'pending'
            )

            # ارسال پردازش به سِلِری به صورت ناهمگام (Async)
            from ..tasks import process_dataset_async
            process_dataset_async.delay(dataset.id)

        return project

    @staticmethod
    def process_dataset_file(dataset):
        """
        دیتاست آپلود شده را پردازش کرده، ستون‌ها و ماتریس مفقوده را بر اساس کل کلیک نمونه‌ها یا کل فایل در دیتابیس ذخیره می‌کند.
        """
        file_path = dataset.file.path
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"فایل {file_path} موجود نیست.")

        # پاکسازی ستون‌های قبلی
        dataset.columns.all().delete()

        # لود دیتاست با لودر چندفرمتِ
        df = DatasetService.load_dataframe(file_path)

        dataset.record_count = len(df)
        dataset.save(update_fields=['record_count'])

        # نمونه‌برداری برای فایل‌های بسیار بزرگ جهت حفظ سرعت و حافظه (تا ۵۰,۰۰۰ سطر)
        if len(df) > 50000:
            df_sample = df.sample(n=50000, random_state=42)
        else:
            df_sample = df

        for col_name in df.columns:
            cleaned_col_name = str(col_name).strip() if col_name else "Unnamed Column"
            series = df_sample[col_name]
            inferred_type = ProfilingService.infer_series_data_type(series)

            Column.objects.create(
                dataset=dataset,
                name=cleaned_col_name,
                data_type=inferred_type
            )

        # تولید و ذخیره نمودار ماتریس داده‌های مفقود
        try:
            missing_chart_buf = VisualizationService.generate_missing_values_chart(df_sample)
            if missing_chart_buf:
                chart_filename = f"missing_matrix_{dataset.id}.png"
                dataset.missing_values_chart.save(chart_filename, ContentFile(missing_chart_buf.getvalue()), save=True)
        except Exception as chart_err:
            print(f"Error generating missing values chart: {chart_err}")

    @staticmethod
    def get_project_detail_context(project):
        dataset = getattr(project, "dataset", None)
        columns = dataset.columns.all() if dataset else []

        type_counts = ProfilingService.get_column_type_counts(columns)

        return {
            "dataset": dataset,
            "file_size_formatted": DatasetService.format_file_size(dataset.file_size) if dataset and dataset.file_size else "0 مگابایت",
            "columns": columns,
            "numeric_count": type_counts["numeric_count"],
            "categorical_count": type_counts["categorical_count"],
        }
