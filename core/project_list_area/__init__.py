# core/project_list_area/__init__.py 

from .project_processor import format_project_data_for_ui
from .project_service import ProjectService

__all__ = [
    'format_project_data_for_ui',
    'ProjectService'
] 