from django.db import models
from django.conf import settings
from analysis_module.models import Project


class ChatSession(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='کاربر'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        null=True,
        blank=True,
        verbose_name='پروژه'
    )
    title = models.CharField('عنوان گفتگو', max_length=255, default='گفتگوی جدید')
    created_at = models.DateTimeField('تاریخ ساخت', auto_now_add=True)
    updated_at = models.DateTimeField('تاریخ بروزرسانی', auto_now=True)

    class Meta:
        db_table = 'chat_session_table'
        verbose_name = 'نشست گفتگو'
        verbose_name_plural = 'نشست‌های گفتگو'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.user.username})"


class ChatMessage(models.Model):
    SENDER_CHOICES = (
        ('user', 'کاربر'),
        ('assistant', 'دستیار'),
        ('system', 'سیستم'),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='نشست گفتگو'
    )
    sender = models.CharField('فرستنده', max_length=20, choices=SENDER_CHOICES, default='user')
    content = models.TextField('متن پیام')
    created_at = models.DateTimeField('تاریخ ارسال', auto_now_add=True)

    class Meta:
        db_table = 'chat_message_table'
        verbose_name = 'پیام گفتگو'
        verbose_name_plural = 'پیام‌های گفتگو'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.sender}] {self.content[:30]}"
