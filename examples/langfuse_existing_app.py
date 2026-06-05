from __future__ import annotations

from pii_redactor.integrations.langfuse import make_mask


def create_langfuse_client():
    from langfuse import Langfuse

    return Langfuse(
        # Keep your existing Langfuse config here: keys, base_url, environment, release, etc.
        mask=make_mask(),
    )
