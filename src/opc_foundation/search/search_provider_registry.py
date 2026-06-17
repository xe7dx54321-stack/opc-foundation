"""Search provider registry – auto-detect and vend provider clients."""
from __future__ import annotations
from .search_provider_base import SearchProviderClient
from .search_schema import SearchQuery, SearchRunResult
from ..providers.provider_doctor import SEARCH_PROVIDER_PRIORITY
from ..providers.env_loader import has_env

_PRIORITY = SEARCH_PROVIDER_PRIORITY   # tavily > brave > serpapi > bing > google_cse


class SearchProviderRegistry:
    """Instantiate, vend, and auto-select search provider clients."""

    def __init__(self, clients: dict[str, SearchProviderClient]) -> None:
        self._clients = clients

    @classmethod
    def from_env(
        cls,
        timeout: int = 20,
        max_retries: int = 2,
    ) -> "SearchProviderRegistry":
        """Build registry from environment variables."""
        from .tavily_client import TavilyClient
        from .brave_client import BraveClient

        clients: dict[str, SearchProviderClient] = {}
        if has_env("TAVILY_API_KEY"):
            clients["tavily"] = TavilyClient(timeout=timeout, max_retries=max_retries)
        if has_env("BRAVE_SEARCH_API_KEY"):
            clients["brave"] = BraveClient(timeout=timeout, max_retries=max_retries)
        return cls(clients)

    def register(self, name: str, client: SearchProviderClient) -> None:
        self._clients[name] = client

    def get_provider(self, name: str) -> SearchProviderClient | None:
        return self._clients.get(name)

    def get_preferred_provider(self) -> SearchProviderClient | None:
        """Return the highest-priority available provider."""
        for name in _PRIORITY:
            client = self._clients.get(name)
            if client and client.is_available():
                return client
        return None

    def available_providers(self) -> list[str]:
        return [name for name, c in self._clients.items() if c.is_available()]

    def search(
        self,
        query: SearchQuery,
        provider_name: str | None = None,
    ) -> SearchRunResult:
        """Run search via named or preferred provider.
        Returns error SearchRunResult if no provider is available.
        """
        from ..run.id_generator import new_id
        from ..run.time_utils import utcnow_iso

        if provider_name:
            client = self.get_provider(provider_name)
            if client is None:
                return SearchRunResult(
                    run_id=new_id("sr_"), provider=provider_name,
                    query=query.query,
                    errors=[f"Provider '{provider_name}' not registered"],
                    started_at=utcnow_iso(), finished_at=utcnow_iso(),
                )
        else:
            client = self.get_preferred_provider()
            if client is None:
                return SearchRunResult(
                    run_id=new_id("sr_"), provider="none",
                    query=query.query,
                    errors=["No search provider available. Set TAVILY_API_KEY or BRAVE_SEARCH_API_KEY."],
                    started_at=utcnow_iso(), finished_at=utcnow_iso(),
                )

        return client.search(query)