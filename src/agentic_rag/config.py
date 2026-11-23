"""Validated settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    gemini_api_key: str = ""
    api_access_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    chroma_mode: Literal["local", "cloud", "firestore"] = "local"
    google_cloud_project: str = ""
    firestore_collection: str = "rag_chunks"
    chroma_path: str = "./data/chroma"
    chroma_collection: str = "documents"
    chroma_api_key: str = ""
    chroma_tenant: str = ""
    chroma_database: str = ""
    top_k: int = Field(default=4, ge=1, le=10)
    max_file_mb: int = Field(default=5, ge=1, le=25)
    max_chunks_per_file: int = Field(default=200, ge=1, le=1000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
