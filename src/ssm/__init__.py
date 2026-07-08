"""Semantic Software Markup Compiler production V1."""

__version__ = "1.3.1"

from .pipeline import CompileOptions, SSMCompiler

__all__ = ["SSMCompiler", "CompileOptions", "__version__"]
