import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis_module', '0008_dataset_status_error_message'),
        ('chat_module', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatsession',
            name='column',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chat_sessions', to='analysis_module.column', verbose_name='ستون'),
        ),
    ]
