from .services import DatasetService, ProfilingService, VisualizationService, AnalysisService


def format_file_size(size_in_bytes):
    return DatasetService.format_file_size(size_in_bytes)


# Re-exports for backwards compatibility
process_dataset_file = DatasetService.process_dataset_file
infer_data_type = ProfilingService.infer_data_type
generate_seaborn_chart = VisualizationService.generate_seaborn_chart
generate_missing_values_chart = VisualizationService.generate_missing_values_chart
