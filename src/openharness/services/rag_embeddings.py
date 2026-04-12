"""Embedding backend helpers for RAG indexing and retrieval."""

from __future__ import annotations

from openai import OpenAI

from openharness.config.settings import Settings, load_settings
from openharness.services.rag_types import EmbeddingBackend


DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"


class OpenAIEmbeddingBackend(EmbeddingBackend):
    """OpenAI-compatible embeddings client."""

    def __init__(
        self, api_key: str, *, base_url: str | None = None, model: str = DEFAULT_EMBEDDING_MODEL
    ) -> None:
        kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._model = model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per text."""
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]


def create_embedding_backend_for_profile(
    profile_name: str,
    *,
    settings: Settings | None = None,
    model: str = DEFAULT_EMBEDDING_MODEL,
) -> EmbeddingBackend:
    """Build an embedding backend using one configured provider profile."""
    resolved_settings = (settings or load_settings()).model_copy(
        update={"active_profile": profile_name}
    )
    _, profile = resolved_settings.resolve_profile(profile_name)
    if profile.api_format != "openai":
        raise ValueError(
            f"Embedding backend currently supports only openai-compatible profiles, got: {profile.api_format}"
        )
    auth = resolved_settings.resolve_auth()
    return OpenAIEmbeddingBackend(
        api_key=auth.value,
        base_url=profile.base_url,
        model=model,
    )


def select_embedding_profile(
    settings: Settings,
    *,
    chat_profile_name: str = "",
    requested_profile_name: str = "",
) -> str:
    """Choose an OpenAI-compatible embedding profile for RAG."""
    profiles = settings.merged_profiles()
    candidates: list[str] = []
    if requested_profile_name:
        candidates.append(requested_profile_name)
    chat_profile = profiles.get(chat_profile_name)
    if chat_profile and chat_profile.provider == "openai" and chat_profile.api_format == "openai":
        candidates.append(chat_profile_name)
    candidates.append("openai-compatible")
    candidates.extend(name for name, profile in profiles.items() if profile.api_format == "openai")

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        profile = profiles.get(candidate)
        if profile is None:
            if candidate == requested_profile_name:
                raise ValueError(f"Unknown embedding profile: {candidate}")
            continue
        if profile.api_format == "openai":
            return candidate
        if candidate == requested_profile_name:
            raise ValueError(
                f"Embedding profile must be openai-compatible, got {profile.api_format}: {candidate}"
            )

    raise ValueError("No openai-compatible profile is available for RAG embeddings.")
