from src.processors.swagger import APIComponentsFilter


def test_filter_on_used_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]

    assert filtered_yaml_dict["components"]["schemas"]["Item"] == {
        "type": "object",
        "properties": {"id": {"type": "integer"}},
    }


def test_filter_on_unused_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_used_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            },
            "/items2/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item2"}}
                            },
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "Item2" in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_unused_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
                "UnusedSchema2": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema2" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_multiple_used_and_unused_schemas():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            },
            "/items2/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item2"}}
                            },
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
                "UnusedSchema2": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert "Item2" in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]
    assert "UnusedSchema2" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_on_duplicated_schema_refs():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items": {
                "get": {
                    "summary": "Get all items",
                    "responses": {
                        "200": {
                            "description": "A list of items",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Item"},
                                    }
                                }
                            },
                        }
                    },
                }
            },
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            },
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "Item2": {"type": "object", "properties": {"id": {"type": "string"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            }
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    assert "components" in filtered_yaml_dict
    assert "schemas" in filtered_yaml_dict["components"]
    assert "Item" in filtered_yaml_dict["components"]["schemas"]
    assert len(filtered_yaml_dict["components"]["schemas"]) == 1
    assert "UnusedSchema" not in filtered_yaml_dict["components"]["schemas"]


def test_filter_schemas_on_multiple_components():
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
                "UnusedSchema": {"type": "object", "properties": {"name": {"type": "string"}}},
            },
            "parameters": {
                "IdParam": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            },
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            },
        },
    }

    components_filter = APIComponentsFilter()
    filtered_yaml_dict = components_filter.filter_schemas(spec)

    expected_filtered_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/items/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "A single item",
                            "content": {
                                "application/json": {"schema": {"$ref": "#/components/schemas/Item"}}
                            },
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "Item": {"type": "object", "properties": {"id": {"type": "integer"}}},
            },
            "parameters": {
                "IdParam": {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}
            },
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                }
            },
        },
    }
    assert filtered_yaml_dict == expected_filtered_spec


# def test_filter_on_duplicated_schema():
#     assert False, "This test is not implemented yet"

# def test_filter_on_no_schemas():
#     assert False, "This test is not implemented yet"

# def test_filter_on_empty_spec():
#     assert False, "This test is not implemented yet"
