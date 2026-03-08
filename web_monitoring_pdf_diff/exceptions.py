"""
Custom exceptions for web-monitoring-pdf-diff.

Mirrors the exception structure used in web-monitoring-diff.
"""


class UndiffableContentError(Exception):
    """
    Raised when the content provided cannot be diffed.

    For example, if the input is not a valid PDF document or if the PDF
    is encrypted and cannot be read.
    """
    pass
