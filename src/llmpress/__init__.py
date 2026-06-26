"""
llmpress — LLM-native prompt compression for source code.

Compresses source code immediately before sending it to an LLM, then
transparently reconstructs the response.  Compression is lossless.
"""

from .core import Compressor, Decompressor, CompressionResult, Dictionary

__version__ = "0.1.0"
__all__ = ["Compressor", "Decompressor", "CompressionResult", "Dictionary"]
