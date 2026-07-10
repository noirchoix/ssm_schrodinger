"""Semantic Software Markup Compiler V1.5.0-dev platform layer."""

__version__ = "1.5.0.dev0"

from .pipeline import CompileOptions, SSMCompiler

__all__ = ["SSMCompiler", "CompileOptions", "__version__"]
