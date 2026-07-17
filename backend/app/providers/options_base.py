from app.providers.intelligence_models import OptionsChainData
from app.providers.models import ProviderHealth


class OptionsDataProvider:
    def get_option_chain(
        self,
        underlying: str,
        max_expirations: int = 4,
    ) -> OptionsChainData:
        raise NotImplementedError

    def get_options_health(self) -> ProviderHealth:
        raise NotImplementedError
