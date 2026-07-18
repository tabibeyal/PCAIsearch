from backend.app.core.model_cache import get_cached_model


def test_get_cached_model_reuses_instance_for_same_key():
    """A second call with the same namespace/model_name must not re-invoke the factory."""
    first = get_cached_model("test-ns-reuse", "model-x", lambda: object())
    second = get_cached_model("test-ns-reuse", "model-x", lambda: object())
    assert first is second


def test_get_cached_model_isolates_by_namespace():
    first = get_cached_model("test-ns-iso-a", "shared-model-name", lambda: object())
    second = get_cached_model("test-ns-iso-b", "shared-model-name", lambda: object())
    assert first is not second
