from django import forms
from analysis_module.models import Project


class ProjectModelForm(forms.ModelForm):
    file = forms.FileField(
        required=False,
        label='فایل دیتاست',
        widget=forms.FileInput(attrs={
            'id': 'datasetFileInput',
            'class': 'd-none',
            'accept': '.csv, .xlsx, .xls, .parquet'
        })
    )

    class Meta:
        model = Project
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-dark',
                'id': 'projectName',
                'placeholder': 'مثلاً: تحلیل فروش فصل بهار',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control form-control-dark',
                'id': 'projectDesc',
                'rows': 3,
                'placeholder': 'توضیح مختصری درباره اهداف این تحلیل...'
            }),
        }


