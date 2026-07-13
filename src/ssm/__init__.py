"""Semantic Software Markup Compiler V2.0 product-platform development release."""

__version__ = "2.0.0.dev0"

from .pipeline import CompileOptions, SSMCompiler

__all__ = ["SSMCompiler", "CompileOptions", "__version__"]
