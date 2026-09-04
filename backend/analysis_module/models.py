from django.db import models
from user_module.models import User


class Project(models.Model):
    name = models.CharField(verbose_name='نام پروژه', max_length=255, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر', related_name='projects')
    created_date = models.DateTimeField('تاریخ ساخت', auto_now_add=True)

    class Meta:
        db_table = 'project_table'
        verbose_name = 'پروژه'
        verbose_name_plural = 'پروژه ها'

    def __str__(self):
        return self.name or f"پروژه {self.id}"


class DataSet(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='پروژه', related_name='datasets', null=True, blank=True)
    file = models.FileField('فایل دیتاست', upload_to='datasets/')
    record_count = models.PositiveIntegerField('تعداد رکوردها', default=0)
    uploaded_at = models.DateTimeField('تاریخ آپلود', auto_now_add=True)

    class Meta:
        db_table = 'dataset_table'
        verbose_name = 'دیتاست'
        verbose_name_plural = 'دیتاست ها'


class Column(models.Model):
    dataset = models.ForeignKey(DataSet, on_delete=models.CASCADE, verbose_name='دیتاست', related_name='columns')
    name = models.CharField('نام ستون', max_length=255)
    data_type = models.CharField('نوع ستون', max_length=255)

    class Meta:
        db_table = 'column_table'
        verbose_name = 'ستون'
        verbose_name_plural = 'ستون ها'

    def __str__(self):
        return self.name


class Analysis(models.Model):
    column = models.ForeignKey(Column, on_delete=models.CASCADE, verbose_name='تحلیل', related_name='analyses')
    mean = models.FloatField('میانگین', blank=True, null=True)
    median = models.FloatField('میانه', blank=True, null=True)
    mode = models.CharField('مد', max_length=255, blank=True, null=True)
    value_counts = models.PositiveIntegerField('تعداد یونیک', default=0)
    visualization = models.ImageField('تجسمی سازی', upload_to='visualizations/', blank=True, null=True)

    class Meta:
        db_table = 'analysis_table'
        verbose_name = 'تحلیل'
        verbose_name_plural = 'تحلیل ها'
