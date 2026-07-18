"""Shared cache for heavy ML models (TextEmbedding, CrossEncoder, ...).

Models are cached globally per (namespace, model_name) so that repeated
instantiation (e.g. one SearchPipeline per test) reuses the already-loaded
model instead of reloading a multi-hundred-MB model and exhausting RAM.
"""
from typing import Callable, TypeVar

T = TypeVar("T")

_caches: dict[str, dict[str, object]] = {}


def get_cached_model(namespace: str, model_name: str, factory: Callable[[], T]) -> T:
    cache = _caches.setdefault(namespace, {})
    if model_name not in cache:
        cache[model_name] = factory()
    return cache[model_name]
