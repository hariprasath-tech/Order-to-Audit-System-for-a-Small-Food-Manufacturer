"""
Pytest configuration and environment defaults for test execution.
"""

import os
import sys

# Ensure required environment variables exist for test execution
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-execution-12345")
os.environ.setdefault("DEBUG", "True")
os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("DEFAULT_VARIANCE_TOLERANCE", "3.00")

# Python 3.14 compatibility patch for django.template.context.BaseContext.__copy__
if sys.version_info >= (3, 14):
    from django.template.context import BaseContext

    def _safe_context_copy(self):
        cls = self.__class__
        duplicate = cls.__new__(cls)
        duplicate.dicts = self.dicts[:]
        return duplicate

    BaseContext.__copy__ = _safe_context_copy
