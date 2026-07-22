from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import median
from typing import Any, Iterable, Literal


TAXONOMY_VERSION = "2026.07.1"
TAXONOMY_EFFECTIVE_FROM = "2026-07-22"
ThemeLifecycle = Literal["active", "experimental", "retired"]
ThemeExposure = Literal["core", "significant", "adjacent", "experimental"]


@dataclass(frozen=True)
class LaunchThemeDefinition:
    id: str
    name: str
    short_name: str
    description: str
    aliases: tuple[str, ...]
    parent_sector_ids: tuple[str, ...]
    related_industry_ids: tuple[str, ...]
    benchmark_symbols: tuple[str, ...]
    minimum_constituents: int
    preferred_minimum_constituents: int
    status: ThemeLifecycle
    taxonomy_version: str
    effective_from: str
    inclusion_rationale: str
    exclusion_notes: str
    retired_at: str | None = None
    replaced_by: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ThemeConstituentMapping:
    theme_id: str
    symbol: str
    exposure: ThemeExposure
    mapping_source: str
    mapping_method: str
    rationale: str
    confidence: float
    effective_from: str
    taxonomy_version: str
    review_status: str
    effective_to: str | None = None
    revenue_or_product_exposure_notes: str | None = None
    benchmark_or_etf_evidence: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


# This is the canonical launch catalog.  The two original reviewed IDs are
# retained verbatim; hyphenated and prior pilot names resolve through aliases.
_THEME_SPECS: tuple[tuple[Any, ...], ...] = (
    ("artificial_intelligence", "Artificial Intelligence", "AI", "Companies whose products enable or apply machine learning at material scale.", ("artificial-intelligence", "ai", "ai_infrastructure", "ai-infrastructure"), ("information_technology", "communication_services"), ("semiconductors", "software", "internet_services"), ("SPY", "QQQ", "XLK")),
    ("semiconductors", "Semiconductors", "Semis", "Designers, manufacturers and equipment suppliers serving semiconductor value chains.", ("semiconductor", "chips"), ("information_technology",), ("semiconductors", "semiconductor_equipment"), ("SPY", "QQQ", "SOXX")),
    ("memory_storage", "Memory & Storage", "Memory", "Suppliers of memory, flash, storage devices and enterprise storage platforms.", ("memory-and-storage", "memory-storage", "data-storage"), ("information_technology",), ("memory", "data_storage"), ("SPY", "QQQ", "XLK")),
    ("data_centers", "Data Centers", "Data Centers", "Operators and infrastructure suppliers with material data-center exposure.", ("data-centers", "cloud_data_centers", "cloud-data-centers"), ("real_estate", "information_technology", "industrials"), ("specialized_reits", "electrical_equipment", "servers"), ("SPY", "QQQ", "XLRE")),
    ("cloud_computing", "Cloud Computing", "Cloud", "Public-cloud platforms and software infrastructure delivered through cloud services.", ("cloud-computing", "public-cloud"), ("information_technology", "communication_services"), ("cloud_platforms", "infrastructure_software"), ("SPY", "QQQ", "SKYY")),
    ("enterprise_software", "Enterprise Software", "Enterprise SW", "Application and platform software used primarily by organizations.", ("enterprise-software", "business-software"), ("information_technology",), ("application_software", "systems_software"), ("SPY", "QQQ", "IGV")),
    ("cybersecurity", "Cybersecurity", "Cyber", "Security platforms spanning endpoint, network, identity, cloud and zero trust.", ("cyber-security", "information-security"), ("information_technology",), ("security_software",), ("SPY", "QQQ", "CIBR")),
    ("networking_infrastructure", "Networking Infrastructure", "Networking", "Network silicon, switching, routing and connectivity infrastructure suppliers.", ("networking-infrastructure", "network-infrastructure"), ("information_technology", "communication_services"), ("communications_equipment", "network_semiconductors"), ("SPY", "QQQ", "XLK")),
    ("robotics_automation", "Robotics & Automation", "Robotics", "Industrial robotics, process automation and machine-vision suppliers.", ("robotics-and-automation", "industrial-automation", "automation"), ("industrials", "information_technology"), ("industrial_machinery", "electronic_equipment"), ("SPY", "XLI", "ROBO")),
    ("digital_advertising", "Digital Advertising", "Digital Ads", "Platforms and technology providers deriving material activity from digital advertising.", ("digital-advertising", "ad-tech", "adtech"), ("communication_services", "information_technology"), ("interactive_media", "advertising_software"), ("SPY", "QQQ", "XLC")),
    ("ecommerce", "E-commerce", "E-commerce", "Marketplaces and commerce platforms with material online transaction exposure.", ("e-commerce", "online-commerce"), ("consumer_discretionary", "information_technology"), ("broadline_retail", "internet_retail"), ("SPY", "QQQ", "IBUY")),
    ("digital_payments", "Digital Payments", "Payments", "Payment networks, processors and digital-wallet platforms.", ("digital-payments", "payments", "fintech-payments"), ("financials", "information_technology"), ("transaction_processing", "payment_networks"), ("SPY", "XLF", "IPAY")),
    ("online_travel", "Online Travel", "Online Travel", "Online travel agencies, booking platforms and digitally distributed travel marketplaces.", ("online-travel", "travel-platforms"), ("consumer_discretionary", "communication_services"), ("travel_services", "internet_marketplaces"), ("SPY", "XLY", "AWAY")),
    ("gaming_interactive_media", "Gaming & Interactive Media", "Gaming", "Publishers and platforms with material video-game and interactive-media exposure.", ("gaming-and-interactive-media", "video-games", "gaming"), ("communication_services", "information_technology"), ("interactive_entertainment", "gaming_platforms"), ("SPY", "XLC", "HERO")),
    ("streaming_digital_entertainment", "Streaming & Digital Entertainment", "Streaming", "Subscription or advertising-supported streaming and digital entertainment platforms.", ("streaming-and-digital-entertainment", "streaming-media", "streaming"), ("communication_services",), ("movies_entertainment", "interactive_media"), ("SPY", "XLC", "QQQ")),
    ("aerospace_defense", "Aerospace & Defense", "Aerospace", "Defense primes and aerospace systems suppliers with material program exposure.", ("aerospace-and-defense", "defense_aerospace", "defense-aerospace"), ("industrials",), ("aerospace_defense",), ("SPY", "XLI", "ITA")),
    ("space_economy", "Space Economy", "Space", "Launch, satellite, communications and space-systems companies.", ("space-economy", "space"), ("industrials", "communication_services"), ("aerospace_defense", "satellite_communications"), ("SPY", "XLI", "ARKX")),
    ("drones_autonomous_systems", "Drones & Autonomous Systems", "Autonomy", "Uncrewed aerial systems and autonomy technology suppliers with material product exposure.", ("drones-and-autonomous-systems", "autonomous-systems", "drones"), ("industrials", "information_technology"), ("aerospace_defense", "electronic_equipment"), ("SPY", "XLI", "ARKQ")),
    ("nuclear_energy", "Nuclear Energy", "Nuclear", "Uranium, nuclear generation and reactor technology companies.", ("nuclear-energy", "uranium"), ("energy", "utilities", "industrials"), ("electric_utilities", "uranium", "industrial_machinery"), ("SPY", "XLU", "URA")),
    ("grid_modernization", "Grid Modernization", "Grid", "Electrical equipment, transmission and grid-management suppliers.", ("grid-modernization", "electric-grid", "smart-grid"), ("industrials", "utilities", "information_technology"), ("electrical_equipment", "utilities", "application_software"), ("SPY", "XLI", "GRID")),
    ("clean_energy", "Clean Energy", "Clean Energy", "Renewable generation, solar, wind and enabling clean-energy technology suppliers.", ("clean-energy", "renewable-energy"), ("energy", "utilities", "industrials", "information_technology"), ("renewable_electricity", "semiconductor_equipment"), ("SPY", "ICLN", "TAN")),
    ("electric_vehicles_batteries", "Electric Vehicles & Batteries", "EV & Batteries", "Electric-vehicle manufacturers and battery or charging value-chain suppliers.", ("electric-vehicles-and-batteries", "ev-and-batteries", "evs"), ("consumer_discretionary", "industrials", "materials"), ("automobiles", "electrical_equipment", "specialty_chemicals"), ("SPY", "XLY", "DRIV")),
    ("biotechnology", "Biotechnology", "Biotech", "Biopharmaceutical companies whose value is driven by biotechnology research and pipelines.", ("biotech", "biotechnology"), ("health_care",), ("biotechnology",), ("SPY", "XLV", "XBI")),
    ("obesity_metabolic_health", "Obesity & Metabolic Health", "Metabolic", "Therapeutics and devices with material obesity, diabetes or metabolic-health exposure.", ("obesity-and-metabolic-health", "metabolic-health", "glp-1"), ("health_care",), ("pharmaceuticals", "health_care_equipment"), ("SPY", "XLV", "XBI")),
    ("medical_technology", "Medical Technology", "MedTech", "Medical devices, diagnostics and technology-enabled clinical tools.", ("medical-technology", "medtech", "medical-devices"), ("health_care",), ("health_care_equipment", "life_sciences_tools"), ("SPY", "XLV", "IHI")),
    ("cryptocurrency_infrastructure", "Cryptocurrency Infrastructure", "Crypto Infra", "Exchanges, miners and infrastructure companies with direct digital-asset network exposure.", ("cryptocurrency-infrastructure", "crypto-infrastructure", "digital-assets"), ("financials", "information_technology"), ("capital_markets", "data_processing", "semiconductors"), ("SPY", "QQQ", "BITQ")),
)


def _definition(spec: tuple[Any, ...]) -> LaunchThemeDefinition:
    theme_id, name, short, description, aliases, parents, industries, benchmarks = spec
    return LaunchThemeDefinition(
        id=theme_id,
        name=name,
        short_name=short,
        description=description,
        aliases=tuple(dict.fromkeys((theme_id, theme_id.replace("_", "-"), name.casefold(), *aliases))),
        parent_sector_ids=parents,
        related_industry_ids=industries,
        benchmark_symbols=benchmarks,
        minimum_constituents=5,
        preferred_minimum_constituents=8,
        status="active",
        taxonomy_version=TAXONOMY_VERSION,
        effective_from=TAXONOMY_EFFECTIVE_FROM,
        inclusion_rationale="Material primary-business, product, revenue, industry, index or expert-curated exposure is required.",
        exclusion_notes="Keyword mentions alone and immaterial diversified exposure are excluded from core membership.",
    )


LAUNCH_THEMES: tuple[LaunchThemeDefinition, ...] = tuple(_definition(spec) for spec in _THEME_SPECS)
RETIRED_THEMES: tuple[LaunchThemeDefinition, ...] = (
    LaunchThemeDefinition(
        id="cloud_data_centers_legacy",
        name="Cloud & Data Centers (Legacy)",
        short_name="Cloud/DC Legacy",
        description="Retired combined pilot concept split into Cloud Computing and Data Centers.",
        aliases=("cloud-and-data-centers-legacy",),
        parent_sector_ids=("information_technology", "real_estate"),
        related_industry_ids=("cloud_platforms", "specialized_reits"),
        benchmark_symbols=("SPY", "QQQ"),
        minimum_constituents=5,
        preferred_minimum_constituents=8,
        status="retired",
        taxonomy_version=TAXONOMY_VERSION,
        effective_from="2026-07-19",
        inclusion_rationale="Preserved for taxonomy lineage only.",
        exclusion_notes="Do not use for new mappings or analytics.",
        retired_at=TAXONOMY_EFFECTIVE_FROM,
        replaced_by="cloud_computing,data_centers",
    ),
)


# Exposure is deliberately explicit.  Equal-weight analytics use every active
# mapped security; exposure tiers affect disclosure and quality gates, not price
# substitution.  No entry is created from a keyword match alone.
_MEMBERS: dict[str, tuple[tuple[str, ThemeExposure], ...]] = {
    "artificial_intelligence": (("NVDA", "core"), ("MSFT", "significant"), ("GOOGL", "significant"), ("AMZN", "significant"), ("META", "significant"), ("AMD", "significant"), ("AVGO", "adjacent"), ("PLTR", "core"), ("ORCL", "adjacent"), ("IBM", "adjacent")),
    "semiconductors": (("NVDA", "core"), ("AVGO", "core"), ("AMD", "core"), ("QCOM", "core"), ("TXN", "core"), ("MU", "core"), ("AMAT", "significant"), ("LRCX", "significant"), ("KLAC", "significant"), ("INTC", "core")),
    "memory_storage": (("MU", "core"), ("SNDK", "core"), ("WDC", "core"), ("STX", "core"), ("MRVL", "significant"), ("NTAP", "significant"), ("P", "significant")),
    "data_centers": (("EQIX", "core"), ("DLR", "core"), ("VRT", "core"), ("SMCI", "significant"), ("DELL", "significant"), ("HPE", "significant"), ("ETN", "adjacent"), ("ANET", "significant"), ("IRM", "adjacent")),
    "cloud_computing": (("MSFT", "core"), ("AMZN", "core"), ("GOOGL", "core"), ("ORCL", "significant"), ("IBM", "significant"), ("SNOW", "core"), ("NET", "significant"), ("DDOG", "significant"), ("NOW", "adjacent")),
    "enterprise_software": (("MSFT", "significant"), ("ORCL", "core"), ("SAP", "core"), ("CRM", "core"), ("NOW", "core"), ("ADBE", "core"), ("INTU", "core"), ("WDAY", "core"), ("PLTR", "significant")),
    "cybersecurity": (("CRWD", "core"), ("PANW", "core"), ("FTNT", "core"), ("ZS", "core"), ("OKTA", "core"), ("CHKP", "core"), ("S", "significant")),
    "networking_infrastructure": (("ANET", "core"), ("CSCO", "core"), ("JNPR", "core"), ("AVGO", "significant"), ("MRVL", "significant"), ("CIEN", "core"), ("NOK", "significant"), ("ERIC", "significant"), ("DELL", "adjacent")),
    "robotics_automation": (("ROK", "core"), ("TER", "significant"), ("ZBRA", "significant"), ("ABB", "core"), ("HON", "significant"), ("EMR", "significant"), ("CGNX", "core"), ("ISRG", "adjacent"), ("FANUY", "core")),
    "digital_advertising": (("GOOGL", "core"), ("META", "core"), ("AMZN", "significant"), ("TTD", "core"), ("PINS", "core"), ("SNAP", "core"), ("ROKU", "significant"), ("RDDT", "significant"), ("APP", "significant")),
    "ecommerce": (("AMZN", "core"), ("SHOP", "core"), ("MELI", "core"), ("EBAY", "core"), ("ETSY", "core"), ("BABA", "core"), ("JD", "core"), ("W", "significant"), ("SE", "significant")),
    "digital_payments": (("V", "core"), ("MA", "core"), ("PYPL", "core"), ("XYZ", "core"), ("FISV", "significant"), ("GPN", "significant"), ("ADYEY", "core"), ("NU", "significant"), ("SOFI", "adjacent")),
    "online_travel": (("BKNG", "core"), ("EXPE", "core"), ("ABNB", "core"), ("TRIP", "core"), ("TCOM", "core"), ("DESP", "core"), ("MMYT", "core")),
    "gaming_interactive_media": (("MSFT", "adjacent"), ("SONY", "significant"), ("NTDOY", "core"), ("EA", "core"), ("TTWO", "core"), ("RBLX", "core"), ("U", "significant"), ("SE", "significant")),
    "streaming_digital_entertainment": (("NFLX", "core"), ("DIS", "significant"), ("WBD", "significant"), ("PSKY", "significant"), ("SPOT", "core"), ("ROKU", "core"), ("AMZN", "adjacent"), ("GOOGL", "significant")),
    "aerospace_defense": (("LMT", "core"), ("NOC", "core"), ("RTX", "core"), ("GD", "core"), ("LHX", "core"), ("BA", "significant"), ("HII", "core"), ("TDG", "significant"), ("BWXT", "significant")),
    "space_economy": (("RKLB", "core"), ("ASTS", "core"), ("RDW", "core"), ("PL", "core"), ("IRDM", "core"), ("VSAT", "significant"), ("LUNR", "core"), ("SPCE", "experimental")),
    "drones_autonomous_systems": (("AVAV", "core"), ("KTOS", "significant"), ("RCAT", "core"), ("ONDS", "experimental"), ("JOBY", "adjacent"), ("ACHR", "adjacent"), ("LMT", "adjacent"), ("NOC", "adjacent")),
    "nuclear_energy": (("CCJ", "core"), ("CEG", "core"), ("VST", "significant"), ("BWXT", "core"), ("SMR", "core"), ("OKLO", "core"), ("LEU", "core"), ("UEC", "core"), ("DNN", "significant")),
    "grid_modernization": (("ETN", "core"), ("HUBB", "core"), ("PWR", "core"), ("GEV", "core"), ("NVT", "significant"), ("ABB", "significant"), ("EMR", "significant"), ("AME", "adjacent"), ("IOT", "adjacent")),
    "clean_energy": (("FSLR", "core"), ("ENPH", "core"), ("SEDG", "core"), ("NXT", "core"), ("RUN", "core"), ("NEE", "significant"), ("BE", "significant"), ("PLUG", "experimental"), ("CSIQ", "core")),
    "electric_vehicles_batteries": (("TSLA", "core"), ("RIVN", "core"), ("LCID", "core"), ("GM", "significant"), ("F", "significant"), ("LI", "core"), ("NIO", "core"), ("XPEV", "core"), ("ALB", "significant"), ("QS", "experimental")),
    "biotechnology": (("AMGN", "core"), ("GILD", "core"), ("REGN", "core"), ("VRTX", "core"), ("BIIB", "core"), ("MRNA", "core"), ("BMRN", "core"), ("ALNY", "core"), ("CRSP", "experimental"), ("NTLA", "experimental")),
    "obesity_metabolic_health": (("LLY", "core"), ("NVO", "core"), ("AMGN", "significant"), ("VKTX", "core"), ("RZLT", "experimental"), ("ALT", "experimental"), ("TNDM", "adjacent"), ("DXCM", "significant")),
    "medical_technology": (("ISRG", "core"), ("MDT", "core"), ("ABT", "core"), ("SYK", "core"), ("BSX", "core"), ("EW", "core"), ("DXCM", "core"), ("PODD", "core"), ("ZBH", "significant")),
    "cryptocurrency_infrastructure": (("COIN", "core"), ("MSTR", "significant"), ("MARA", "core"), ("RIOT", "core"), ("CLSK", "core"), ("HUT", "core"), ("IREN", "core"), ("CIFR", "core"), ("HOOD", "significant")),
}


def _mapping(theme: LaunchThemeDefinition, symbol: str, exposure: ThemeExposure) -> ThemeConstituentMapping:
    method = "primary_business_exposure" if exposure == "core" else "reliable_product_or_revenue_exposure" if exposure == "significant" else "industry_or_curated_support"
    correction = {
        ("digital_payments", "XYZ"): "Verified same-entity ticker successor to SQ; Polygon CIK/FIGI continuity and the 2025-01-17/2025-01-21 provider boundary are retained in security history.",
        ("digital_payments", "FISV"): "Verified same-entity ticker successor to FI; Polygon CIK/FIGI continuity and the 2025-11-10/2025-11-11 provider boundary are retained in security history.",
        ("streaming_digital_entertainment", "PSKY"): "Verified merger successor to PARA; the 2025-08-06/2025-08-07 provider boundary and distinct successor identity are retained in security history.",
    }.get((theme.id, symbol))
    return ThemeConstituentMapping(
        theme_id=theme.id,
        symbol=symbol,
        exposure=exposure,
        mapping_source="stage8.75-curated-company-disclosure-and-industry-review",
        mapping_method=method,
        rationale=f"{symbol} has {exposure} exposure to {theme.name} under the documented launch inclusion hierarchy.",
        confidence={"core": 0.95, "significant": 0.85, "adjacent": 0.72, "experimental": 0.55}[exposure],
        effective_from=TAXONOMY_EFFECTIVE_FROM,
        taxonomy_version=TAXONOMY_VERSION,
        review_status="curated_launch_catalog",
        revenue_or_product_exposure_notes=" ".join(filter(None, ("Exposure is tiered; diversified issuers are not automatically treated as core.", correction))),
        benchmark_or_etf_evidence=f"Theme benchmark set: {', '.join(theme.benchmark_symbols)}.",
    )


THEME_MAPPINGS: tuple[ThemeConstituentMapping, ...] = tuple(
    _mapping(theme, symbol, exposure)
    for theme in LAUNCH_THEMES
    for symbol, exposure in _MEMBERS[theme.id]
)


def _retired_mapping(theme_id: str, symbol: str, exposure: ThemeExposure, provider_transition_date: str) -> ThemeConstituentMapping:
    """Preserve the exact launch mapping lineage for a verified ticker transition."""
    theme = next(item for item in LAUNCH_THEMES if item.id == theme_id)
    original = _mapping(theme, symbol, exposure)
    return ThemeConstituentMapping(
        **{
            **original.model_dump(),
            # The mapping amendment occurred on the launch taxonomy effective
            # date. Provider-symbol history below retains the older market-date
            # boundary independently from taxonomy lineage.
            "effective_to": TAXONOMY_EFFECTIVE_FROM,
            "review_status": "retired_verified_provider_ticker_transition",
            "revenue_or_product_exposure_notes": (
                f"The thematic exposure is unchanged; the approved Polygon identity/history audit "
                f"verified the provider-symbol transition after {provider_transition_date}."
            ),
        }
    )


# These records are lineage only.  They are not active mappings and therefore
# do not alter the reviewed 227-row launch exposure catalog.
RETIRED_THEME_MAPPINGS: tuple[ThemeConstituentMapping, ...] = (
    _retired_mapping("digital_payments", "SQ", "core", "2025-01-17"),
    _retired_mapping("digital_payments", "FI", "significant", "2025-11-10"),
    _retired_mapping("streaming_digital_entertainment", "PARA", "significant", "2025-08-06"),
)


class ThemeRegistry:
    def __init__(
        self,
        definitions: Iterable[LaunchThemeDefinition] = (*LAUNCH_THEMES, *RETIRED_THEMES),
        mappings: Iterable[ThemeConstituentMapping] = THEME_MAPPINGS,
        mapping_history: Iterable[ThemeConstituentMapping] = RETIRED_THEME_MAPPINGS,
    ) -> None:
        self.definitions = tuple(definitions)
        self.mappings = tuple(mappings)
        self.mapping_history = tuple(mapping_history)
        self._by_id = {item.id: item for item in self.definitions}
        self._alias_to_id: dict[str, str] = {}
        for item in self.definitions:
            for alias in item.aliases:
                self._alias_to_id[self._key(alias)] = item.id
        self._by_theme: dict[str, tuple[ThemeConstituentMapping, ...]] = {
            theme.id: tuple(item for item in self.mappings if item.theme_id == theme.id)
            for theme in self.definitions
        }
        symbols = sorted({item.symbol for item in self.mappings})
        self._by_symbol = {
            symbol: tuple(item for item in self.mappings if item.symbol == symbol)
            for symbol in symbols
        }

    @staticmethod
    def _key(value: str) -> str:
        return "-".join(value.strip().casefold().replace("_", "-").split())

    def resolve(self, value: str) -> str:
        key = self._key(value)
        canonical = self._alias_to_id.get(key)
        if canonical is None:
            raise ValueError(f"unknown_theme_id:{value}")
        return canonical

    def definition(self, value: str) -> LaunchThemeDefinition | None:
        try:
            return self._by_id.get(self.resolve(value))
        except (TypeError, ValueError):
            return None

    def launch(self) -> tuple[LaunchThemeDefinition, ...]:
        return tuple(item for item in self.definitions if item.status == "active")

    def constituents(self, value: str) -> tuple[ThemeConstituentMapping, ...]:
        definition = self.definition(value)
        return self._by_theme.get(definition.id, ()) if definition else ()

    def themes_for_symbol(self, symbol: str) -> tuple[ThemeConstituentMapping, ...]:
        order = {"core": 0, "significant": 1, "adjacent": 2, "experimental": 3}
        return tuple(sorted(self._by_symbol.get(symbol.strip().upper(), ()), key=lambda item: (order[item.exposure], item.theme_id)))

    def validate(self, known_symbols: set[str] | None = None) -> list[dict[str, str]]:
        issues: list[dict[str, str]] = []
        ids: set[str] = set()
        aliases: dict[str, str] = {}
        for definition in self.definitions:
            if definition.id in ids:
                issues.append({"code": "duplicate_theme_id", "subject": definition.id})
            ids.add(definition.id)
            if not definition.parent_sector_ids:
                issues.append({"code": "invalid_parent_sector", "subject": definition.id})
            for alias in definition.aliases:
                key = self._key(alias)
                if key in aliases and aliases[key] != definition.id:
                    issues.append({"code": "duplicate_alias", "subject": alias})
                aliases[key] = definition.id
        seen: set[tuple[str, str]] = set()
        for mapping in self.mappings:
            key = (mapping.theme_id, mapping.symbol)
            if key in seen:
                issues.append({"code": "duplicate_mapping", "subject": ":".join(key)})
            seen.add(key)
            definition = self._by_id.get(mapping.theme_id)
            if definition is None:
                issues.append({"code": "unknown_theme", "subject": mapping.theme_id})
            elif definition.status == "retired":
                issues.append({"code": "retired_theme_mapping", "subject": mapping.theme_id})
            if mapping.exposure not in {"core", "significant", "adjacent", "experimental"}:
                issues.append({"code": "invalid_exposure", "subject": mapping.symbol})
            if not mapping.rationale.strip():
                issues.append({"code": "missing_rationale", "subject": mapping.symbol})
            if not mapping.mapping_source.strip() or not mapping.mapping_method.strip():
                issues.append({"code": "missing_provenance", "subject": mapping.symbol})
            if mapping.taxonomy_version != TAXONOMY_VERSION:
                issues.append({"code": "mapping_version_mismatch", "subject": mapping.symbol})
            if known_symbols is not None and mapping.symbol not in known_symbols:
                issues.append({"code": "unknown_symbol", "subject": mapping.symbol})
        for definition in self.launch():
            members = self.constituents(definition.id)
            if len(members) < definition.minimum_constituents:
                issues.append({"code": "sparse_theme", "subject": definition.id})
            if members and 1 / len(members) >= 0.5:
                issues.append({"code": "constituent_dominance", "subject": definition.id})
        return issues

    def statistics(self) -> dict[str, Any]:
        exposures = {name: sum(item.exposure == name for item in self.mappings) for name in ("core", "significant", "adjacent", "experimental")}
        counts = [len(self.constituents(item.id)) for item in self.launch()]
        return {
            "taxonomy_version": TAXONOMY_VERSION,
            "active": len(self.launch()),
            "experimental": sum(item.status == "experimental" for item in self.definitions),
            "retired": sum(item.status == "retired" for item in self.definitions),
            "launch_ready": sum(len(self.constituents(item.id)) >= item.minimum_constituents for item in self.launch()),
            "total_mappings": len(self.mappings),
            "retired_mapping_lineage": len(self.mapping_history),
            "core": exposures["core"],
            "significant": exposures["significant"],
            "adjacent": exposures["adjacent"],
            "experimental_mappings": exposures["experimental"],
            "theme_counts": {"active": len(self.launch()), "experimental": sum(item.status == "experimental" for item in self.definitions), "retired": sum(item.status == "retired" for item in self.definitions)},
            "mapping_counts": exposures,
            "symbols_mapped_to_multiple_themes": sum(len(items) > 1 for items in self._by_symbol.values()),
            "mappings_with_complete_provenance": sum(bool(item.mapping_source and item.mapping_method and item.rationale) for item in self.mappings),
            "median_constituents": median(counts) if counts else 0,
            "minimum_constituents": min(counts, default=0),
            "maximum_constituents": max(counts, default=0),
        }


_registry: ThemeRegistry | None = None


def get_launch_theme_registry() -> ThemeRegistry:
    global _registry
    if _registry is None:
        _registry = ThemeRegistry()
    return _registry
