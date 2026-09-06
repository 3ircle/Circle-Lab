import csv
import io
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import pandas as pd
from django.core.files.base import ContentFile
from .models import Column, Analysis


def format_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0 مگابایت"
    size_in_mb = size_in_bytes / (1024 * 1024)
    if size_in_mb >= 1024:
        size_in_gb = size_in_mb / 1024
        return f"{size_in_gb:.2f} گیگابایت"
    return f"{size_in_mb:.2f} مگابایت"


def infer_data_type(value_str):
    if not value_str or str(value_str).strip() == "":
        return None
    val = str(value_str).strip()

    try:
        int(val)
        return "عدد صحیح (Integer)"
    except ValueError:
        pass

    try:
        float(val)
        return "عدد اعشاری (Float)"
    except ValueError:
        pass

    if val.lower() in ["true", "false", "بله", "خیر", "1", "0"]:
        return "منطقی (Boolean)"

    return "رشته متنی (String)"


def process_dataset_file(dataset):
    """
    دیتاست آپلود شده را پردازش کرده، تعداد رکوردها و ستون‌ها به همراه نوع داده آن‌ها را استخراج می‌کند.
    """
    file_path = dataset.file.path
    if not os.path.exists(file_path):
        return

    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".csv", ".txt"]:
        try:
            encoding = "utf-8-sig"
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.readline()
            except UnicodeDecodeError:
                encoding = "utf-8"

            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)

                delimiter = ","
                if sample:
                    if sample.count(";") > sample.count(","):
                        delimiter = ";"
                    elif sample.count("\t") > sample.count(","):
                        delimiter = "\t"

                reader = csv.reader(f, delimiter=delimiter)
                try:
                    headers = next(reader)
                except StopIteration:
                    return

                headers = [h.strip() if h else f"Column_{i+1}" for i, h in enumerate(headers)]

                sample_rows = []
                record_count = 0
                for row in reader:
                    record_count += 1
                    if len(sample_rows) < 50:
                        sample_rows.append(row)

                dataset.record_count = record_count
                dataset.save()

                for col_idx, col_name in enumerate(headers):
                    types_found = set()
                    for row in sample_rows:
                        if col_idx < len(row):
                            cell_val = row[col_idx]
                            inferred = infer_data_type(cell_val)
                            if inferred:
                                types_found.add(inferred)

                    if "رشته متنی (String)" in types_found:
                        final_type = "رشته متنی (String)"
                    elif "عدد اعشاری (Float)" in types_found:
                        final_type = "عدد اعشاری (Float)"
                    elif "عدد صحیح (Integer)" in types_found:
                        final_type = "عدد صحیح (Integer)"
                    elif "منطقی (Boolean)" in types_found:
                        final_type = "منطقی (Boolean)"
                    else:
                        final_type = "رشته متنی (String)"

                    Column.objects.create(
                        dataset=dataset,
                        name=col_name,
                        data_type=final_type
                    )

            # تولید و ذخیره نمودار ماتریس داده‌های مفقود در دیتابیس
            try:
                df = pd.read_csv(file_path, encoding=encoding, errors="replace", delimiter=delimiter)
                missing_chart_buf = generate_missing_values_chart(df)
                if missing_chart_buf:
                    chart_filename = f"missing_matrix_{dataset.id}.png"
                    dataset.missing_values_chart.save(chart_filename, ContentFile(missing_chart_buf.getvalue()), save=True)
            except Exception as chart_err:
                print(f"Error generating missing values chart: {chart_err}")

        except Exception as e:
            print(f"Error processing CSV dataset: {e}")


def generate_seaborn_chart(df, col_name, data_type):
    """
    تولید نمودار با Seaborn با استایل Dark Mode کاستوم متناسب با CircleLab
    """
    fig, ax = plt.subplots(figsize=(6, 3.2), dpi=100)

    # Dark Theme Colors
    fig.patch.set_facecolor('#1E293B')
    ax.set_facecolor('#1E293B')
    ax.tick_params(colors='#CBD5E1', labelsize=8)
    ax.xaxis.label.set_color('#CBD5E1')
    ax.yaxis.label.set_color('#CBD5E1')
    ax.title.set_color('#FFFFFF')
    for spine in ax.spines.values():
        spine.set_color('#334155')

    ax.grid(True, linestyle='--', alpha=0.2, color='#CBD5E1')

    series = df[col_name].dropna()

    if data_type in ["عدد صحیح (Integer)", "عدد اعشاری (Float)"]:
        numeric_series = pd.to_numeric(series, errors='coerce').dropna()
        if not numeric_series.empty:
            sns.histplot(numeric_series, kde=True, ax=ax, color='#22D3EE', edgecolor='#0F172A', alpha=0.7)
            ax.set_ylabel('فراوانی', fontname='DejaVu Sans', fontsize=9)
    else:
        counts = series.astype(str).value_counts().head(8)
        if not counts.empty:
            palette = ['#6366F1', '#22D3EE', '#A855F7', '#34D399', '#F59E0B', '#EF4444', '#818CF8', '#C084FC']
            sns.barplot(x=counts.index, y=counts.values, ax=ax, palette=palette[:len(counts)], hue=counts.index, legend=False)
            ax.set_ylabel('تعداد', fontname='DejaVu Sans', fontsize=9)
            plt.xticks(rotation=25, ha='right')

    ax.set_xlabel(col_name, fontsize=9)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf


def generate_missing_values_chart(df):
    """
    تولید نمودار ماتریس مقادیر مفقوده (MSNO Matrix / Missing Values Matrix)
    با پشتیبانی از تعداد بالای ستون‌ها و استایل Dark Mode کاستوم CircleLab
    """
    num_cols = len(df.columns)
    if num_cols == 0:
        return None

    # محاسبه عرض پویا بر اساس تعداد ستون‌ها تا اسکوئیش و ناخوانا نشوند
    fig_width = max(10.0, num_cols * 0.38)
    fig, ax = plt.subplots(figsize=(fig_width, 4.2), dpi=100)

    # Dark Theme Colors
    fig.patch.set_facecolor('#1E293B')
    ax.set_facecolor('#1E293B')

    try:
        import missingno as msno
        # اگر پکیج missingno موجود باشد
        msno.matrix(
            df,
            sparkline=False,
            color=(0.133, 0.827, 0.933), # Cyan #22D3EE
            fontsize=9,
            labels=True,
            ax=ax
        )
        ax.set_facecolor('#1E293B')
        ax.tick_params(colors='#CBD5E1', labelsize=8)
    except Exception:
        # Fallback به Matplotlib / Seaborn در صورت عدم حضور یا خطای missingno
        # نمونه‌برداری یکنواخت تا ۳۰۰ سطر برای سرعت و وضوح ماتریس
        if len(df) > 300:
            df_sampled = df.iloc[::len(df)//300]
        else:
            df_sampled = df

        not_null_matrix = df_sampled.notnull().values
        cmap = mcolors.ListedColormap(['#334155', '#22D3EE']) # Grey for missing, Cyan for present

        ax.imshow(not_null_matrix, aspect='auto', cmap=cmap, interpolation='none')

        ax.set_xticks(range(num_cols))
        ax.set_xticklabels(df.columns, rotation=45, ha='right', colors='#CBD5E1', fontsize=8)
        ax.set_yticks([])
        ax.tick_params(colors='#CBD5E1')

        for spine in ax.spines.values():
            spine.set_color('#334155')

    ax.set_title('ماتریس مقادیر مفقوده (Missing Values Matrix)', color='#FFFFFF', fontsize=11, pad=12)
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return buf

