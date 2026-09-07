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

    @staticmethod
    def get_column_detailed_analysis(column: Column):
        """
        محاسبه تحلیل عمیق ستون شامل value_counts، مقادیر مفقوده، آمار توصیفی و ۵ ستون با بیشترین همبستگی
        """
        dataset = column.dataset
        if not dataset or not dataset.file:
            return None, "دیتاستی یافت نشد."

        file_path = dataset.file.path
        if not os.path.exists(file_path):
            return None, "فایل دیتاست در سرور یافت نشد."

        try:
            df = DatasetService.load_dataframe(file_path)
            col_name = column.name

            if col_name not in df.columns:
                return None, f"ستون «{col_name}» در فایل یافت نشد."

            series = df[col_name]
            total_records = len(series)

            # ۱. محاسبه value_counts (۱۰ مقدار پرتکرار)
            val_counts_series = series.value_counts(dropna=False).head(10)
            value_counts_list = []
            for val, count in val_counts_series.items():
                if pd.isna(val):
                    val_str = "(داده مفقود / NaN)"
                else:
                    val_str = str(val)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                pct = round((count / total_records) * 100, 1) if total_records > 0 else 0
                value_counts_list.append({
                    "value": val_str,
                    "count": int(count),
                    "percentage": pct
                })

            # ۲. اطلاعات مقادیر مفقوده و یونیک
            missing_count = int(series.isna().sum())
            missing_pct = round((missing_count / total_records) * 100, 2) if total_records > 0 else 0
            unique_count = int(series.nunique(dropna=True))

            # ۳. آمار توصیفی کامل
            is_numeric = column.data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]
            stats_dict = {
                "missing_count": missing_count,
                "missing_percentage": missing_pct,
                "unique_count": unique_count,
                "total_records": total_records,
                "mean": None,
                "median": None,
                "std": None,
                "min": None,
                "max": None,
                "q25": None,
                "q75": None,
                "skewness": None,
                "mode": None
            }

            if is_numeric:
                cleaned = series.astype(str).str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip()
                num_series = pd.to_numeric(cleaned, errors='coerce').dropna()
                if not num_series.empty:
                    stats_dict["mean"] = round(float(num_series.mean()), 2)
                    stats_dict["median"] = round(float(num_series.median()), 2)
                    stats_dict["std"] = round(float(num_series.std()), 2) if len(num_series) > 1 else 0.0
                    stats_dict["min"] = round(float(num_series.min()), 2)
                    stats_dict["max"] = round(float(num_series.max()), 2)
                    stats_dict["q25"] = round(float(num_series.quantile(0.25)), 2)
                    stats_dict["q75"] = round(float(num_series.quantile(0.75)), 2)
                    try:
                        skew_val = num_series.skew()
                        stats_dict["skewness"] = round(float(skew_val), 2) if not pd.isna(skew_val) else None
                    except Exception:
                        stats_dict["skewness"] = None
                    mode_s = num_series.mode()
                    stats_dict["mode"] = str(round(mode_s.iloc[0], 2)) if not mode_s.empty else None
            else:
                mode_s = series.dropna().mode()
                stats_dict["mode"] = str(mode_s.iloc[0]) if not mode_s.empty else None

            # ۴. محاسبه ۵ ستون با بیشترین همبستگی (Top 5 Correlations)
            corr_df = pd.DataFrame()
            if is_numeric:
                target_series = pd.to_numeric(series.astype(str).str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip(), errors='coerce')
            else:
                target_series = pd.Series(pd.factorize(series.astype(str))[0], index=series.index)

            other_columns = column.dataset.columns.exclude(id=column.id)
            col_name_to_obj = {c.name: c for c in other_columns}

            for other_col in other_columns:
                if other_col.name in df.columns:
                    other_s = df[other_col.name]
                    if other_col.data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
                        corr_df[other_col.name] = pd.to_numeric(other_s.astype(str).str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip(), errors='coerce')
                    else:
                        corr_df[other_col.name] = pd.Series(pd.factorize(other_s.astype(str))[0], index=other_s.index)

            top_correlations = []
            if not corr_df.empty and target_series.notnull().sum() > 1:
                corr_results = []
                for other_name in corr_df.columns:
                    other_series = corr_df[other_name]
                    valid_mask = target_series.notnull() & other_series.notnull()
                    if valid_mask.sum() > 2:
                        try:
                            c_val = float(target_series[valid_mask].corr(other_series[valid_mask]))
                            if not pd.isna(c_val):
                                other_obj = col_name_to_obj.get(other_name)
                                corr_results.append({
                                    "column_id": other_obj.id if other_obj else None,
                                    "column_name": other_name,
                                    "data_type": other_obj.data_type if other_obj else "نامشخص",
                                    "correlation": round(c_val, 3),
                                    "abs_correlation": abs(c_val)
                                })
                        except Exception:
                            pass

                corr_results.sort(key=lambda x: x["abs_correlation"], reverse=True)
                top_correlations = [{
                    "column_id": item["column_id"],
                    "column_name": item["column_name"],
                    "data_type": item["data_type"],
                    "correlation": item["correlation"]
                } for item in corr_results[:5]]

            analysis = column.analyses.last()
            visualization_url = analysis.visualization.url if (analysis and analysis.visualization) else None

            return {
                "column": {
                    "id": column.id,
                    "name": column.name,
                    "data_type": column.data_type,
                },
                "value_counts": value_counts_list,
                "stats": stats_dict,
                "top_correlations": top_correlations,
                "visualization_url": visualization_url,
                "project_name": dataset.project.name if dataset.project else "",
            }, None

        except Exception as e:
            return None, f"خطا در تحلیل عمیق ستون: {str(e)}"
