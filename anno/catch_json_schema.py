CATCH_JSON_SCHEMA = {
    "id": "http://localhost:8555/catch-annotation.json",
    "description": "schema for catch webannotations",
    "type": "object",
    "required": ["id", "body", "target",
        "platform", "permissions", "creator", "schema_version"
    ],
    "properties": {
        "id": {
            "type": "string"
        },
        "type": {
            "type": "string"
        },
        "schema_version": {
            "type": "string"
        },
        "created": {
            "type": "string",
            "format": "dateTime"
        },
        "modified": {
            "type": "string",
            "format": "dateTime"
        },
        "creator": {
            "$ref": "#/definitions/Creator"
        },
        "permissions": {
            "$ref": "#/definitions/Permissions"
        },
        "platform": {
            "$ref": "#/definitions/Platform"
        },
        "body": {
            "$ref": "#/definitions/Body"
        },
        "target": {
            "$ref": "#/definitions/Target"
        }
    },
    "definitions": {
        "Body": {
            "type": "object",
            "required": ["type", "items"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "Choice",
                        "List"
                    ]
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/BodyItem"
                    }
                }
            }
        },
        "BodyItem": {
            "type": "object",
            "required": ["type", "purpose", "value"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "TextualBody"
                    ]
                },
                "format": {
                    "type": "string",
                    "enum": [
                        "text/html",
                        "text/plain"
                    ]
                },
                "purpose": {
                    "type": "string",
                    "enum": [
                        "commenting",
                        "tagging",
                        "replying"
                    ]
                },
                "value": {
                    "type": "string"
                }
            }
        },
        "Target": {
            "type": "object",
            "required": ["type", "items"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "Choice",
                        "List"
                    ]
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "items": {
                        "$ref": "#/definitions/TargetItem"
                    }
                }
            }
        },
        "TargetItem": {
            "type": "object",
            "required": ["source", "type"],
            "properties": {
                "source": {
                    "type": "string"
                },
                "type": {
                    "type": "string",
                    "enum": [
                        "Text",
                        "Image",
                        "Video",
                        "Audio",
                        "Thumbnail",
                        "Annotation",
                        "Choice"
                    ]
                },
                "format": {
                    "type": "string"
                },
                "selector": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": [
                                "Choice",
                                "List"
                            ]
                        },
                        "items": {
                            "type": "array",
                            "minItems": 0,
                            "items": {
                                "$ref": "#/definitions/SelectorItem"
                            }
                        }
                    }
                },
                "scope": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "enum": [
                                "Viewport"
                            ]
                        },
                        "value": {
                            "type": "string"
                        }
                    }
                }
            }
        },
        "SelectorItem": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "RangeSelector",
                        "XPathSelector",
                        "TextPositionSelector",
                        "TextQuoteSelector",
                        "CssSelector",
                        "FragmentSelector",
                        "SvgSelector"
                    ]
                },
                "conformsTo": {
                    "type": "string"
                },
                "refinedBy": {
                    "type": "array",
                    "minItems": 0,
                    "items": {
                        "$ref": "#/definitions/SelectorItem"
                    }
                },
                "value": {
                    "type": "string"
                }
            }
        },
        "Creator": {
            "type": "object",
            "required": ["id", "name"],
            "properties": {
                "id": {
                    "type": "string"
                },
                "name": {
                    "type": "string"
                }
            }
        },
        "Permissions": {
            "type": "object",
            "required": ["can_read", "can_update", "can_delete", "can_admin"],
            "properties": {
                "can_read": {
                    "$ref": "#/definitions/Permission"
                },
                "can_update": {
                    "$ref": "#/definitions/Permission"
                },
                "can_delete": {
                    "$ref": "#/definitions/Permission"
                },
                "can_admin": {
                    "$ref": "#/definitions/Permission"
                }
            }
        },
        "Permission": {
            "type": "array",
            "minItems": 0,
            "items": {
                "type": "string"
            },
            "uniqueItems": True
        },
        "Platform": {
            "type": "object",
            "required": ["platform_name", "contextId"],
            "properties": {
                "platform_name": {
                    "type": "string"
                },
                "contextId": {
                    "type": "string"
                },
                "collectionId": {
                    "type": "string"
                },
                "target_source_id": {
                    "type": "string"
                }
            }
        },
        "Tags": {
            "type": "array",
            "minItems": 0,
            "items": {
                "type": "string"
            }
        },
        "SearchResult": {
            "type": "object",
            "properties": {
                "total": {
                    "type": "integer",
                    "description": "total of objects found for search"
                },
                "size": {
                    "type": "integer",
                    "description": "number of objects returned in this list"
                },
                "limit": {
                    "type": "integer",
                    "description": "max number of objects requested"
                },
                "offset": {
                    "type": "integer",
                    "description": "requested offset"
                },
                "rows": {
                    "type": "array",
                    "minItems": 0,
                    "items": {
                        "$ref": "#/definitions/Annotation"
                    }
                }
            }
        },
        "Error": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "integer",
                    "format": "int32"
                },
                "message": {
                    "type": "string"
                },
                "fields": {
                    "type": "string"
                }
            }
        }
    }
}
