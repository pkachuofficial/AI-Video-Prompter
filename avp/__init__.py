"""
avp — AI Video Prompter
Top-level package for the generative drama production pipeline.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ai-video-prompter")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["__version__"]
