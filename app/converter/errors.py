"""Errors raised by the conversion engine.

A ConversionError always carries a short, teacher-facing message (the ones shown in
the UI, matching the examples in the brief: "No Google Form HTML found", "Unsupported
question structure", "Failed to extract answers"). Raising one aborts conversion of
*that single ZIP only* — the pipeline catches it per-file so the rest of a batch keeps
processing.
"""


class ConversionError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message
