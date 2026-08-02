"""Semantic Software Markup Compiler V2.5 development release."""

__version__ = "2.5.0.dev0"

from .pipeline import CompileOptions, SSMCompiler
from .product.compiler import SchrodingerProductCompiler

__all__ = ["SSMCompiler", "SchrodingerProductCompiler", "CompileOptions", "__version__"]
