from dependency_injector import containers, providers

from ..processors.postman_processor import PostmanProcessor
from ..processors.swagger import (
    APIDefinitionMerger,
    APIDefinitionSplitter,
    FileLoader,
    APIComponentsFilter,
)
from ..processors.swagger_processor import SwaggerProcessor
from ..services.file_service import FileService


class ProcessorsAdapter(containers.DeclarativeContainer):
    """Adapter for processor components."""

    config = providers.Configuration()

    file_service = providers.Factory(FileService)

    file_loader = providers.Factory(FileLoader)
    splitter = providers.Factory(APIDefinitionSplitter)
    merger = providers.Factory(APIDefinitionMerger)
    components_filter = providers.Factory(APIComponentsFilter)

    swagger_processor = providers.Factory(
        SwaggerProcessor,
        file_loader=file_loader,
        splitter=splitter,
        merger=merger,
        components_filter=components_filter,
        file_service=file_service,
        config=config,
    )
    postman_processor = providers.Factory(
        PostmanProcessor,
        file_service=file_service,
        config=config,
    )
