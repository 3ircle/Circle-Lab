
import csv
import os
from .models import Column


def format_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0 مگابایت"
    size_in_mb = size_in_bytes / (1024 * 1024)
    if size_in_mb >= 1024:
        size_in_gb = size_in_mb / 1024
        return f"{size_in_gb:.2f} گیگابایت"
    return f"{size_in_mb:.2f} مگابایت"


def infer_data_type(value_str):
    if not value_str or value_str.strip() == "":
        return None
    val = value_str.strip()

    # Try Integer
    try:
        int(val)
        return "عدد صحیح (Integer)"
    except ValueError:
        pass

    # Try Float
    try:
        float(val)
        return "عدد اعشاری (Float)"
    except ValueError:
        pass

    # Try Boolean
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

    if ext == ".csv":
        try:
            # سعی در خواندن فایل CSV با انکودینگ‌های متداول
            encoding = "utf-8-sig"
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    f.readline()
            except UnicodeDecodeError:
                encoding = "utf-8"

            with open(file_path, "r", encoding=encoding, errors="replace") as f:
                # تشخص خودکار separator در صورت امکان
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

                # بررسی ۵۰ سطر اول جهت تشخیص نوع داده هر ستون
                sample_rows = []
                record_count = 0
                for row in reader:
                    record_count += 1
                    if len(sample_rows) < 50:
                        sample_rows.append(row)

                dataset.record_count = record_count
                dataset.save()

                # استخراج نوع داده ستون‌ها
                for col_idx, col_name in enumerate(headers):
                    types_found = set()
                    for row in sample_rows:
                        if col_idx < len(row):
                            cell_val = row[col_idx]
                            inferred = infer_data_type(cell_val)
                            if inferred:
                                types_found.add(inferred)

                    # تعیین نوع نهایی
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

        except Exception as e:
            print(f"Error processing CSV dataset: {e}")

