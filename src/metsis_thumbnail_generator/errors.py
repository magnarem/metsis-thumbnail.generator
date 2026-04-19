"""Project-specific exceptions."""


class ThumbnailGeneratorError(Exception):
    """Base exception for the thumbnail generator."""


class ConfigError(ThumbnailGeneratorError):
    """Raised when configuration is missing or invalid."""


class InputError(ThumbnailGeneratorError):
    """Raised when input metadata cannot be processed."""


class SolrError(ThumbnailGeneratorError):
    """Raised when Solr operations fail."""
