from typing import Optional

import structlog

log = structlog.get_logger(__name__)

from annatar.debrid.alldebrid import AllDebridProvider
from annatar.debrid.debrid_service import DebridService
from annatar.debrid.debridlink import DebridLink
from annatar.debrid.premiumize_provider import PremiumizeProvider
from annatar.debrid.real_debrid_provider import RealDebridProvider

_providers: list[DebridService] = [
    RealDebridProvider(api_key="", source_ip=""),
]


def register_provider(prov: "DebridService"):
    _providers.append(prov)


def all_providers() -> list[DebridService]:
    return _providers


def list_providers() -> list[dict[str, str]]:
    return [{"id": p.id(), "name": p.name()} for p in _providers]


def get_provider(provider_name: str, api_key: str, source_ip: str) -> Optional[DebridService]:
    log.info("getting provider", provider_name=provider_name, api_key=api_key, source_ip=source_ip)
    for p in _providers:
        if p.id() == provider_name:
            return p.__class__(api_key=api_key, source_ip=source_ip)
    return None
