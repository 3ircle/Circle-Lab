import re
import pandas as pd


class ProfilingService:
    @staticmethod
    def infer_series_data_type(series: pd.Series) -> str:
        """
        تشخیص هوشمند و معنایی (Semantic Data Profiling) نوع داده یک ستون با استفاده از Pandas
        پشتیبانی از Datetime، اعداد فرمت‌شده ($، %، ،)، Boolean دقیق و تفکیک Categorical از Text.
        """
        non_null_series = series.dropna()
        if non_null_series.empty:
            return "رشته متنی (String)"

        # 1. پاکسازی ابتدایی کاراکترهای فرمت‌دهی عددی ($، €، ﷼، %، ،)
        str_series = non_null_series.astype(str).str.strip()
        cleaned_series = str_series.str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip()

        # 2. بررسی عددی (Numeric)
        try:
            numeric_vals = pd.to_numeric(cleaned_series, errors='raise')
            if (numeric_vals % 1 == 0).all():
                return "عدد صحیح (Integer)"
            return "عدد اعشاری (Float)"
        except (ValueError, TypeError):
            pass

        # 3. بررسی تاریخ و زمان (Datetime)
        # فقط در صورتی تاریخ ارزیابی می‌شود که کاراکترهای جداکننده تاریخ مانند / یا - دارند
        has_date_delimiters = str_series.str.contains(r'[-/:\.T]', regex=True).any()
        if has_date_delimiters:
            try:
                dt_vals = pd.to_datetime(non_null_series, errors='coerce', format='mixed')
                if dt_vals.notnull().mean() >= 0.8:
                    return "تاریخ/زمان (Datetime)"
            except Exception:
                pass

        # 4. بررسی دقیق منطقی (Boolean)
        unique_vals = set(str_series.str.lower().unique())
        bool_sets = [{"true", "false"}, {"بله", "خیر"}, {"yes", "no"}]
        if any(unique_vals.issubset(b_set) for b_set in bool_sets):
            return "منطقی (Boolean)"

        # 5. تفکیک متنی (Text) از دسته‌ای (Categorical)
        unique_count = series.nunique()
        total_count = len(series)
        if unique_count <= 30 or (total_count > 0 and (unique_count / total_count) <= 0.05):
            return "دسته‌ای (Categorical)"

        return "رشته متنی (String)"

    @staticmethod
    def infer_data_type(value_str):
        """
        سازگاری با متدهای قدیمی برای تشخیص سلولی تک‌مقداری
        """
        if not value_str or str(value_str).strip() == "":
            return None
        return ProfilingService.infer_series_data_type(pd.Series([value_str]))

    @staticmethod
    def calculate_column_stats(series: pd.Series, data_type: str) -> dict:
        """
        محاسبه آمار توصیفی (میانگین، میانه، مد و یونیک‌ها) برای یک ستون
        """
        mean_val = None
        median_val = None
        mode_val = None
        unique_counts = int(series.nunique())

        if data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
            cleaned_series = series.astype(str).str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip()
            numeric_series = pd.to_numeric(cleaned_series, errors='coerce').dropna()
            if not numeric_series.empty:
                mean_val = float(numeric_series.mean())
                median_val = float(numeric_series.median())
                mode_series = numeric_series.mode()
                if not mode_series.empty:
                    mode_val = str(round(mode_series.iloc[0], 2))
        else:
            mode_series = series.dropna().mode()
            if not mode_series.empty:
                mode_val = str(mode_series.iloc[0])

        return {
            "mean": mean_val,
            "median": median_val,
            "mode": mode_val,
            "value_counts": unique_counts,
        }

    @staticmethod
    def calculate_detailed_column_stats(series: pd.Series, data_type: str) -> dict:
        """
        محاسبه آمار تفصیلی ستون شامل min, max, std, quartiles, missing count & percentage
        """
        total_count = len(series)
        null_count = int(series.isnull().sum())
        null_percentage = float(round((null_count / total_count * 100), 2)) if total_count > 0 else 0.0
        unique_count = int(series.nunique())

        stats = {
            "total_count": total_count,
            "null_count": null_count,
            "null_percentage": null_percentage,
            "unique_count": unique_count,
            "data_type": data_type,
            "min": None,
            "max": None,
            "std": None,
            "mean": None,
            "median": None,
            "q25": None,
            "q50": None,
            "q75": None,
            "iqr": None,
            "skewness": None,
            "mode": None
        }

        non_null_series = series.dropna()
        if non_null_series.empty:
            return stats

        if data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
            cleaned_series = series.astype(str).str.replace(r'[\$,%€﷼,]', '', regex=True).str.strip()
            numeric_series = pd.to_numeric(cleaned_series, errors='coerce').dropna()

            if not numeric_series.empty:
                stats["min"] = float(numeric_series.min())
                stats["max"] = float(numeric_series.max())
                stats["std"] = float(numeric_series.std()) if len(numeric_series) > 1 else 0.0
                stats["mean"] = float(numeric_series.mean())
                stats["median"] = float(numeric_series.median())
                stats["q25"] = float(numeric_series.quantile(0.25))
                stats["q50"] = float(numeric_series.quantile(0.50))
                stats["q75"] = float(numeric_series.quantile(0.75))
                stats["iqr"] = float(stats["q75"] - stats["q25"])
                try:
                    skew_val = numeric_series.skew()
                    stats["skewness"] = round(float(skew_val), 2) if not pd.isna(skew_val) else None
                except Exception:
                    stats["skewness"] = None
                mode_series = numeric_series.mode()
                if not mode_series.empty:
                    stats["mode"] = str(round(mode_series.iloc[0], 2))
        else:
            mode_series = non_null_series.mode()
            if not mode_series.empty:
                stats["mode"] = str(mode_series.iloc[0])
            str_series = non_null_series.astype(str)
            stats["min"] = str(str_series.min())
            stats["max"] = str(str_series.max())

        return stats

    @staticmethod
    def get_value_counts_breakdown(series: pd.Series, top_n: int = 10) -> list:
        """
        جدول تفکیکی کامل top value_counts به همراه درصد و تعداد
        """
        total_records = len(series)
        if total_records == 0:
            return []

        counts_series = series.value_counts(dropna=False).head(top_n)
        breakdown = []

        for rank, (val, count) in enumerate(counts_series.items(), start=1):
            if pd.isna(val):
                val_str = "(داده مفقود / NaN)"
            else:
                val_str = str(val)
                if len(val_str) > 50:
                    val_str = val_str[:47] + "..."
            pct = round((count / total_records) * 100, 1)
            breakdown.append({
                "rank": rank,
                "value": val_str,
                "count": int(count),
                "percentage": pct
            })

        return breakdown

    @staticmethod
    def get_column_type_counts(columns) -> dict:
        """
        شمارش ستون‌های عددی و متنی/دسته‌ای
        """
        numeric_count = 0
        categorical_count = 0
        for col in columns:
            if col.data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
                numeric_count += 1
            else:
                categorical_count += 1
        return {
            "numeric_count": numeric_count,
            "categorical_count": categorical_count,
        }
