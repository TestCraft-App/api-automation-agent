from typing import Dict, Any

from ...utils.logger import Logger
from .components_filter_strategies.openapi_v3_schema_filter import OpenAPIv3SchemaFilter
from .components_filter_strategies.openapi_v2_schema_filter import OpenAPIv2SchemaFilter


class APIComponentsFilter:
    """Reduces API definition components to only those that are necessary."""

    def __init__(self):
        self.logger = Logger.get_logger(__name__)

    def filter_schemas(self, api_definition: Dict[str, Any]) -> Dict[str, Any]:
        if "swagger" in api_definition:
            return OpenAPIv2SchemaFilter().filter(api_definition)
        if "openapi" in api_definition:
            return OpenAPIv3SchemaFilter().filter(api_definition)
