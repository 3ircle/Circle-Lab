import os
import logging
from django.conf import settings
from analysis_module.models import Project
from chat_module.models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)


class ChatService:
    @staticmethod
    def build_system_prompt(project: Project) -> str:
        """
        کامپایل کردن کانتکست دیتاست شامل اطلاعات پروژه، دیتاست، ستون‌ها و آمار توصیفی تحلیل‌ها
        """
        system_prompt = (
            "شما یک دستیار هوش مصنوعی متخصص تحلیل داده در سامانه CircleLab هستید.\n"
            "پاسخ‌ها را به زبان فارسی روان، دقیق و کاربردی ارائه دهید.\n\n"
        )

        if not project:
            return system_prompt + "هیچ پروژه‌ای برای این گفتگو انتخاب نشده است."

        dataset = getattr(project, 'dataset', None)

        system_prompt += f"--- اطلاعات پروژه و دیتاست فعال ---\n"
        system_prompt += f"نام پروژه: {project.name or 'بدون نام'}\n"
        system_prompt += f"توضیحات پروژه: {project.description or 'توضیحاتی ثبت نشده است.'}\n"

        if dataset:
            file_name = os.path.basename(dataset.file.name) if dataset.file else "فایل دیتاست"
            system_prompt += f"نام فایل دیتاست: {file_name}\n"
            system_prompt += f"تعداد کل سطرها (رکوردها): {dataset.record_count}\n"
            system_prompt += f"وضعیت پردازش: {dataset.get_status_display()}\n\n"

            columns = dataset.columns.prefetch_related('analyses').all()
            if columns.exists():
                system_prompt += "ساختار ستون‌ها و خلاصه آمار توصیفی:\n"
                for idx, col in enumerate(columns, start=1):
                    system_prompt += f"{idx}. ستون «{col.name}» (نوع: {col.data_type}):\n"
                    analyses = col.analyses.all()
                    if analyses.exists():
                        for ana in analyses:
                            stats = []
                            if ana.mean is not None:
                                stats.append(f"میانگین: {ana.mean:.2f}")
                            if ana.median is not None:
                                stats.append(f"میانه: {ana.median:.2f}")
                            if ana.mode:
                                stats.append(f"مد: {ana.mode}")
                            if ana.value_counts:
                                stats.append(f"تعداد مقادیر منحصر‌به‌فرد: {ana.value_counts}")
                            if stats:
                                system_prompt += f"   - آمار توصیفی: " + " | ".join(stats) + "\n"
                    else:
                        system_prompt += "   - تحلیلی ثبت نشده است.\n"
            else:
                system_prompt += "هیچ ستونی ثبت نشده است.\n"
        else:
            system_prompt += "دیتاستی به این پروژه متصل نشده است.\n"

        system_prompt += (
            "\nدستورالعمل پاسخگویی:\n"
            "- از اطلاعات آماری بالا برای پاسخ به سوالات کاربر و ارائه تحلیل دقیق استفاده کنید.\n"
            "- در صورت درخواست کاربر برای کدهای پایتون یا رسم نمودار، کدهای اجرایی کامل با pandas و seaborn/matplotlib ارائه دهید.\n"
        )
        return system_prompt

    @staticmethod
    def build_column_system_prompt(column, detailed_data: dict) -> str:
        """
        تولید پرامپت سیستمی متمرکز بر یک ستون خاص همراه با تمامی جزئیات آماری، value_counts و همبستگی‌ها
        """
        system_prompt = (
            "شما یک دستیار هوش مصنوعی متخصص تحلیل داده، آمار کاربردی و یادگیری ماشین در سامانه CircleLab هستید.\n"
            "شما در حال بررسی و تحلیل عمیق یک ستون خاص از دیتاست می‌باشید. پاسخ‌ها را به زبان فارسی روان، دقیق، ساختاریافته و با بینش‌های عمیق آماری ارائه دهید.\n\n"
            f"--- مشخصات ستون مورد بررسی ---\n"
            f"نام ستون: «{column.name}»\n"
            f"نوع داده (Data Type): {column.data_type}\n"
        )
        if detailed_data.get("project_name"):
            system_prompt += f"نام پروژه: {detailed_data['project_name']}\n"

        stats = detailed_data.get("stats", {})
        system_prompt += (
            f"تعداد کل رکوردها: {stats.get('total_records', 0)}\n"
            f"تعداد مقادیر مفقوده (Missing / NaN): {stats.get('missing_count', 0)} ({stats.get('missing_percentage', 0)}%)\n"
            f"تعداد مقادیر یونیک (Unique): {stats.get('unique_count', 0)}\n"
        )

        if stats.get("mean") is not None:
            system_prompt += f"میانگین (Mean): {stats.get('mean')}\n"
        if stats.get("median") is not None:
            system_prompt += f"میانه (Median): {stats.get('median')}\n"
        if stats.get("std") is not None:
            system_prompt += f"انحراف معیار (Standard Deviation): {stats.get('std')}\n"
        if stats.get("min") is not None and stats.get("max") is not None:
            system_prompt += f"حداقل (Min): {stats.get('min')} | حداکثر (Max): {stats.get('max')}\n"
        if stats.get("q25") is not None and stats.get("q75") is not None:
            system_prompt += f"چارک اول (Q25): {stats.get('q25')} | چارک سوم (Q75): {stats.get('q75')}\n"
        if stats.get("skewness") is not None:
            system_prompt += f"ضریب چولگی (Skewness): {stats.get('skewness')}\n"
        if stats.get("mode"):
            system_prompt += f"مد (Mode): {stats.get('mode')}\n"

        val_counts = detailed_data.get("value_counts", [])
        if val_counts:
            system_prompt += "\nتوزیع فراوانی مقادیر برتر (Top Value Counts):\n"
            for item in val_counts:
                system_prompt += f"- مقدار: «{item['value']}» -> فراوانی: {item['count']} سطر ({item['percentage']}%)\n"

        top_corrs = detailed_data.get("top_correlations", [])
        if top_corrs:
            system_prompt += "\n۵ ستون با بالاترین میزان همبستگی (Top Correlations):\n"
            for corr in top_corrs:
                system_prompt += f"- ستون «{corr['column_name']}» (نوع: {corr['data_type']}) -> ضریب همبستگی: {corr['correlation']}\n"

        system_prompt += (
            "\nدستورالعمل پاسخگویی:\n"
            "- از تمام اطلاعات آماری و همبستگی بالا به عنوان مبنای پاسخ و تحلیل علمی استفاده کنید.\n"
            "- در صورت وجود ناهنجاری (مثل درصد بالای داده مفقود، چولگی شدید یا همبستگی بالا)، علت و نحوه مدیریت آن را توضیح دهید.\n"
            "- در صورت نیاز به کدنویسی، کدهای استاندارد Pandas / Seaborn / Sklearn ارائه دهید.\n"
        )
        return system_prompt

    @classmethod
    def stream_column_chat_response(cls, column, detailed_data: dict, user_prompt: str, history_messages: list = None):
        """
        استریم پاسخ چت اختصاصی ستون با کانتکست غنی آماری
        """
        system_prompt = cls.build_column_system_prompt(column, detailed_data)
        messages = [{"role": "system", "content": system_prompt}]

        if history_messages:
            for msg in history_messages:
                messages.append(msg)

        messages.append({"role": "user", "content": user_prompt})

        api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            yield "کلید API هوش مصنوعی (OPENAI_API_KEY) در تنظیمات سرور ثبت نشده است."
            return

        try:
            import openai
            base_url = getattr(settings, 'OPENAI_BASE_URL', None) or os.getenv('AI_BASE_URL', None) or os.getenv('OPENAI_BASE_URL', None)
            client_kwargs = {'api_key': api_key}
            if base_url:
                client_kwargs['base_url'] = base_url

            client = openai.OpenAI(**client_kwargs)
            model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"\n[خطا در برقراری ارتباط با مدل هوش مصنوعی: {str(e)}]"
        """
        ارسال درخواست به OpenAI و استریم پاسخ به صورت Chunkهای متنی
        همچنین ذخیره پیام نهایی کاربر و دستیار در دیتابیس
        """
        system_prompt = cls.build_system_prompt(session.project)
        messages = [{"role": "system", "content": system_prompt}]

        history = session.messages.order_by('created_at')
        for msg in history:
            role = "user" if msg.sender == "user" else ("assistant" if msg.sender == "assistant" else "system")
            messages.append({"role": role, "content": msg.content})

        api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
        if not api_key:
            err_msg = "کلید OpenAI API (OPENAI_API_KEY) در تنظیمات سیستم قرار نگرفته است."
            ChatMessage.objects.create(session=session, sender="assistant", content=err_msg)
            yield err_msg
            return

        try:
            import openai
            base_url = getattr(settings, 'OPENAI_BASE_URL', None) or os.getenv('AI_BASE_URL', None) or os.getenv('OPENAI_BASE_URL', None)
            client_kwargs = {'api_key': api_key}
            if base_url:
                client_kwargs['base_url'] = base_url

            client = openai.OpenAI(**client_kwargs)
            model_name = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True
            )

            full_content = []
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_content.append(text_chunk)
                    yield text_chunk

            assistant_reply = "".join(full_content)
            if assistant_reply:
                ChatMessage.objects.create(
                    session=session,
                    sender='assistant',
                    content=assistant_reply
                )
                if session.title == "گفتگوی جدید" and user_prompt:
                    session.title = user_prompt[:30] + ("..." if len(user_prompt) > 30 else "")
                session.save()

        except Exception as e:
            error_text = f"\n[خطا در برقراری ارتباط با مدل OpenAI: {str(e)}]"
            ChatMessage.objects.create(session=session, sender="assistant", content=error_text)
            yield error_text
