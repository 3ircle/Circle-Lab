from celery import shared_task
from .models import DataSet, Column
from .services import DatasetService, AnalysisService


@shared_task(bind=True, max_retries=3)
def process_dataset_async(self, dataset_id: int):
    """
    پردازش ناهمگام (Async) فایل دیتاست در بک‌گراند با سِلِری به همراه مدیریت وضعیت‌ها
    """
    try:
        dataset = DataSet.objects.get(pk=dataset_id)
        dataset.status = 'processing'
        dataset.save(update_fields=['status'])

        DatasetService.process_dataset_file(dataset)

        dataset.status = 'completed'
        dataset.error_message = None
        dataset.save(update_fields=['status', 'error_message'])

    except DataSet.DoesNotExist:
        pass
    except Exception as exc:
        try:
            dataset = DataSet.objects.get(pk=dataset_id)
            dataset.status = 'failed'
            dataset.error_message = str(exc)
            dataset.save(update_fields=['status', 'error_message'])
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=5)


@shared_task(bind=True, max_retries=3)
def analyze_single_column_async(self, column_id: int, sample_percent: int = 100):
    """
    تحلیل ناهمگام (Async) یک ستون در بک‌گراند با سِلِری
    """
    try:
        column = Column.objects.get(pk=column_id)
        result, error = AnalysisService.analyze_single_column(column, sample_percent)
        if error:
            raise Exception(error["data"].get("error", "Error analyzing column"))
        return result
    except Column.DoesNotExist:
        pass
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5)
