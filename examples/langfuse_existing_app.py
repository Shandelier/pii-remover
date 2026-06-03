from __future__ import annotations

from pii_redactor.integrations.langfuse import make_mask


def create_langfuse_client():
    from langfuse import Langfuse

    return Langfuse(
        # Keep your existing Langfuse config here: keys, base_url, environment, release, etc.
        mask=make_mask(),
    )


def create_langfuse_client_with_bards_ai_model():
    from langfuse import Langfuse

    return Langfuse(
        # Requires: python3 -m pip install -e '.[local]'
        mask=make_mask(backend="local"),
    )
