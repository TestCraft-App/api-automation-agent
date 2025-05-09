from enum import Enum, auto


class DataSource(Enum):
    SWAGGER = auto()
    POSTMAN = auto()
    NONE = auto()


def get_processor_for_data_source(data_source: DataSource, container):
    """
    Returns the appropriate processor based on the data source.

    Args:
        data_source: The data source type (DataSource enum)
        container: The dependency injection container

    Returns:
        The processor instance

    Raises:
        ValueError: If the data source is not supported
    """
    match data_source:
        case DataSource.SWAGGER:
            return container.swagger_processor()
        case DataSource.POSTMAN:
            return container.postman_processor()
        case _:
            raise ValueError(f"Unsupported data source: {data_source}")
