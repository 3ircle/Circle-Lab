from rest_framework import serializers
from .models import Project, DataSet, Column, Analysis


class AnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Analysis
        fields = ['id', 'column', 'mean', 'median', 'mode', 'value_counts', 'visualization']


class ColumnSerializer(serializers.ModelSerializer):
    analysis = serializers.SerializerMethodField()

    class Meta:
        model = Column
        fields = ['id', 'name', 'data_type', 'analysis']

    def get_analysis(self, obj):
        analysis = obj.analyses.last()
        if analysis:
            return AnalysisSerializer(analysis, context=self.context).data
        return None


class DataSetSerializer(serializers.ModelSerializer):
    columns = ColumnSerializer(many=True, read_only=True)
    column_count = serializers.IntegerField(source='columns.count', read_only=True)

    class Meta:
        model = DataSet
        fields = ['id', 'file', 'file_size', 'record_count', 'uploaded_at', 'columns', 'column_count']


class ProjectSerializer(serializers.ModelSerializer):
    dataset = DataSetSerializer(read_only=True)
    created_date_formatted = serializers.DateTimeField(source='created_date', format='%Y-%m-%d %H:%M', read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_date', 'created_date_formatted', 'dataset']
