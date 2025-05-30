from pydantic import BaseModel, field_validator


class ScopedConfig(BaseModel):
    """Plugin Config Here"""

    base_url: str = "https://bithesis.bitnp.net"
    """Base URL of the VitePress site, without a trailing slash."""

    @field_validator("base_url")
    @classmethod
    def check_base_url(cls, v: str) -> str:
        assert v.startswith("https://")
        assert not v.endswith("/")
        return v


class Config(BaseModel):
    search_faq: ScopedConfig = ScopedConfig()
