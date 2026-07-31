from research_agent.providers.base import CAP_KEYWORD_VOLUME, ProviderAdapter
from research_agent.providers.impl.dataforseo import DataForSeoAdapter
from research_agent.providers.registry import ProviderRegistry


class _Down(ProviderAdapter):
    provider_id = "ahrefs"

    def capabilities(self):
        return {CAP_KEYWORD_VOLUME}

    def cost_estimate(self, capability, n_items):
        return 0.0

    def health(self):
        return False  # đang chết


def test_fallback_chain_from_providers_yaml():
    reg = ProviderRegistry(adapters={})
    chain = reg.fallback_chain(CAP_KEYWORD_VOLUME)
    # providers.yaml: keyword_volume: [dataforseo, google_keyword_planner, ahrefs, semrush]
    assert chain[0] == "dataforseo"
    assert "ahrefs" in chain


def test_select_orders_by_chain_and_filters_registered():
    reg = ProviderRegistry(adapters={"dataforseo": DataForSeoAdapter()})
    chosen = reg.select(CAP_KEYWORD_VOLUME)
    assert [a.provider_id for a in chosen] == ["dataforseo"]


def test_select_skips_unhealthy_provider():
    reg = ProviderRegistry(
        adapters={"dataforseo": DataForSeoAdapter(), "ahrefs": _Down()}
    )
    chosen = [a.provider_id for a in reg.select(CAP_KEYWORD_VOLUME)]
    assert "ahrefs" not in chosen
    assert chosen[0] == "dataforseo"


def test_first_available():
    reg = ProviderRegistry(adapters={"dataforseo": DataForSeoAdapter()})
    assert reg.first_available(CAP_KEYWORD_VOLUME).provider_id == "dataforseo"
    assert reg.first_available("nonexistent_capability") is None
