"""Polymarket REST client.

Uses Gamma for market discovery and CLOB for live pricing.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import requests
except ImportError:  # pragma: no cover - environment fallback
    requests = None


logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
CLOB_API_BASE = "https://clob.polymarket.com"
CACHE_TTL_SECONDS = 300


@dataclass
class PolymarketMarket:
    market_id: str
    question: str
    yes_probability: float
    no_probability: float
    volume_24h: float
    last_updated: str
    raw: dict[str, Any] | None = None


class PolymarketClient:
    def __init__(self, cache_ttl_seconds: int = CACHE_TTL_SECONDS, timeout: int = 10):
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout = timeout
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_lock = threading.Lock()
        self._session = requests.Session() if requests else None
        if self._session is not None:
            self._session.headers.update(
                {
                    "User-Agent": "atlas-ibkr-trader/1.0",
                    "Accept": "application/json",
                }
            )

    def search_markets(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        cache_key = f"search:{query.lower()}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        markets: list[dict[str, Any]] = []
        raw_results = self._gamma_search(query=query, limit=limit)
        for raw in raw_results[:limit]:
            normalized = self._normalize_market(raw)
            if normalized:
                markets.append(asdict(normalized))

        self._set_cached(cache_key, markets)
        return markets

    def get_market_odds(self, market_id: str) -> dict[str, Any]:
        cache_key = f"odds:{market_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        raw_market = self._resolve_market(market_id)
        if not raw_market:
            fallback = self._empty_market(market_id, f"Market not found: {market_id}")
            self._set_cached(cache_key, fallback)
            return fallback

        normalized = self._normalize_market(raw_market)
        if normalized is None:
            fallback = self._empty_market(market_id, "Unable to normalize market")
            self._set_cached(cache_key, fallback)
            return fallback

        clob_odds = self._get_clob_odds(raw_market)
        if clob_odds:
            normalized.yes_probability = clob_odds.get(
                "yes_probability", normalized.yes_probability
            )
            normalized.no_probability = clob_odds.get(
                "no_probability", normalized.no_probability
            )

        result = asdict(normalized)
        self._set_cached(cache_key, result)
        return result

    def get_geopolitical_markets(self) -> list[dict[str, Any]]:
        queries = ["Iran", "oil", "war", "ceasefire"]
        return self._dedupe_and_collect(queries)

    def get_commodity_markets(self) -> list[dict[str, Any]]:
        queries = ["oil", "gold", "wheat", "corn"]
        return self._dedupe_and_collect(queries)

    def _dedupe_and_collect(self, queries: list[str]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for query in queries:
            for market in self.search_markets(query, limit=10):
                key = market.get("market_id") or market.get("question", "")
                if key in seen:
                    continue
                seen.add(key)
                results.append(market)
        return results

    def _gamma_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        if not self._session:
            return []

        candidates = [
            ("/markets", {"search": query, "limit": limit}),
            ("/markets", {"query": query, "limit": limit}),
            ("/search", {"query": query, "limit": limit}),
            (
                "/markets",
                {"limit": max(limit, 25), "sort": "volume24hr", "order": "desc"},
            ),
        ]

        for path, params in candidates:
            try:
                payload = self._get_json(GAMMA_API_BASE, path, params=params)
                markets = self._extract_markets(payload)
                if not markets:
                    continue
                if query:
                    filtered = self._filter_markets(markets, query)
                    if filtered:
                        return filtered
                return markets
            except Exception as exc:
                logger.debug("Gamma search failed for %s via %s: %s", query, path, exc)

        return []

    def _resolve_market(self, market_id: str) -> dict[str, Any] | None:
        if not self._session:
            return None

        candidates = [
            (f"/markets/{market_id}", None),
            ("/markets", {"id": market_id}),
            ("/markets", {"slug": market_id}),
            ("/markets", {"clob_token_id": market_id}),
        ]

        for path, params in candidates:
            try:
                payload = self._get_json(GAMMA_API_BASE, path, params=params)
                if isinstance(payload, dict):
                    market = payload.get("market") or payload.get("data") or payload
                    if isinstance(market, dict):
                        return market
                elif isinstance(payload, list) and payload:
                    first = payload[0]
                    if isinstance(first, dict):
                        return first
            except Exception as exc:
                logger.debug(
                    "Market resolution failed for %s via %s: %s", market_id, path, exc
                )

        # Last resort: search by id/text
        matches = self._gamma_search(query=market_id, limit=5)
        return matches[0] if matches else None

    def _get_clob_odds(self, market: dict[str, Any]) -> dict[str, float]:
        token_ids = self._extract_token_ids(market)
        if not token_ids:
            return self._probabilities_from_market_fields(market)

        token_results: dict[str, dict[str, Any]] = {}
        for outcome, token_id in token_ids.items():
            book = self._get_order_book(token_id)
            if not book:
                continue
            token_results[outcome] = book

        if "YES" in token_results and "NO" in token_results:
            yes_price = self._price_from_book(token_results["YES"])
            no_price = self._price_from_book(token_results["NO"])
            if yes_price is None and no_price is not None:
                yes_price = max(0.0, min(1.0, 1.0 - no_price))
            if no_price is None and yes_price is not None:
                no_price = max(0.0, min(1.0, 1.0 - yes_price))
            if yes_price is not None and no_price is not None:
                total = yes_price + no_price
                if total > 0:
                    yes = yes_price / total
                    no = no_price / total
                    return {"yes_probability": yes, "no_probability": no}

        return self._probabilities_from_market_fields(market)

    def _get_order_book(self, token_id: str) -> dict[str, Any] | None:
        if not self._session:
            return None

        candidates = [
            ("/book", {"token_id": token_id}),
            ("/orderbook", {"token_id": token_id}),
            (f"/book/{token_id}", None),
            (f"/orderbook/{token_id}", None),
        ]

        for path, params in candidates:
            try:
                payload = self._get_json(CLOB_API_BASE, path, params=params)
                if isinstance(payload, dict):
                    return payload
            except Exception as exc:
                logger.debug(
                    "CLOB book lookup failed for %s via %s: %s", token_id, path, exc
                )

        return None

    def _price_from_book(self, book: dict[str, Any]) -> Optional[float]:
        bids = self._extract_levels(book.get("bids"), highest=True)
        asks = self._extract_levels(book.get("asks"), highest=False)

        best_bid = bids[0][0] if bids else None
        best_ask = asks[0][0] if asks else None

        if best_bid is not None and best_ask is not None:
            return round((best_bid + best_ask) / 2, 6)
        return best_ask if best_ask is not None else best_bid

    def _extract_levels(self, levels: Any, highest: bool) -> list[tuple[float, float]]:
        parsed: list[tuple[float, float]] = []
        if not isinstance(levels, list):
            return parsed

        for level in levels:
            price = size = None
            if isinstance(level, dict):
                price = level.get("price") or level.get("p")
                size = level.get("size") or level.get("s") or 0
            elif isinstance(level, (list, tuple)) and len(level) >= 2:
                price, size = level[0], level[1]
            if price is None:
                continue
            try:
                parsed.append((float(price), float(size or 0)))
            except (TypeError, ValueError):
                continue

        parsed.sort(key=lambda item: item[0], reverse=highest)
        return parsed

    def _extract_token_ids(self, market: dict[str, Any]) -> dict[str, str]:
        token_ids: dict[str, str] = {}

        clob_ids = market.get("clobTokenIds") or market.get("clob_token_ids")
        outcomes = market.get("outcomes") or market.get("tokens")

        if isinstance(clob_ids, list):
            if isinstance(outcomes, list) and len(outcomes) == len(clob_ids):
                for outcome, token_id in zip(outcomes, clob_ids):
                    outcome_name = self._normalize_outcome_name(outcome)
                    if outcome_name and token_id:
                        token_ids[outcome_name] = str(token_id)
            elif len(clob_ids) == 2:
                token_ids["YES"] = str(clob_ids[0])
                token_ids["NO"] = str(clob_ids[1])

        if isinstance(outcomes, list):
            for outcome in outcomes:
                if not isinstance(outcome, dict):
                    continue
                outcome_name = self._normalize_outcome_name(
                    outcome.get("outcome")
                    or outcome.get("name")
                    or outcome.get("label")
                )
                token_id = (
                    outcome.get("token_id")
                    or outcome.get("tokenId")
                    or outcome.get("clobTokenId")
                )
                if outcome_name and token_id:
                    token_ids[outcome_name] = str(token_id)

        return token_ids

    def _normalize_outcome_name(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip().upper()
        if text in {"YES", "Y", "TRUE"}:
            return "YES"
        if text in {"NO", "N", "FALSE"}:
            return "NO"
        return None

    def _probabilities_from_market_fields(
        self, market: dict[str, Any]
    ) -> dict[str, float]:
        yes = self._coerce_probability(
            market.get("yesProbability")
            or market.get("yes_probability")
            or market.get("probability")
            or market.get("lastPrice")
            or market.get("last_price")
            or self._first_outcome_price(market.get("outcomePrices"))
            or self._first_outcome_price(market.get("outcome_prices"))
        )

        if yes is None:
            yes = 0.5

        no = 1.0 - yes
        return {"yes_probability": round(yes, 6), "no_probability": round(no, 6)}

    def _first_outcome_price(self, values: Any) -> Optional[float]:
        if isinstance(values, str):
            values = values.replace("[", "").replace("]", "").split(",")
        if isinstance(values, (list, tuple)) and values:
            return self._coerce_probability(values[0])
        if isinstance(values, dict):
            for key in ("yes", "YES", "0"):
                if key in values:
                    return self._coerce_probability(values[key])
        return None

    def _coerce_probability(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            prob = float(value)
        except (TypeError, ValueError):
            return None
        if prob > 1.0:
            prob = prob / 100.0
        return max(0.0, min(1.0, prob))

    def _normalize_market(self, raw: dict[str, Any]) -> Optional[PolymarketMarket]:
        question = self._extract_question(raw)
        if not question:
            return None

        market_id = str(
            raw.get("id")
            or raw.get("market_id")
            or raw.get("conditionId")
            or raw.get("condition_id")
            or question
        )
        volume_24h = self._extract_volume_24h(raw)
        probabilities = self._probabilities_from_market_fields(raw)
        updated = self._extract_timestamp(raw)

        return PolymarketMarket(
            market_id=market_id,
            question=question,
            yes_probability=probabilities["yes_probability"],
            no_probability=probabilities["no_probability"],
            volume_24h=volume_24h,
            last_updated=updated,
            raw=raw,
        )

    def _extract_question(self, raw: dict[str, Any]) -> str | None:
        for key in ("question", "title", "name", "market", "description"):
            value = raw.get(key)
            if value:
                return str(value).strip()
        return None

    def _extract_volume_24h(self, raw: dict[str, Any]) -> float:
        for key in (
            "volume24hr",
            "volume_24h",
            "volume24hUSD",
            "liquidity",
            "volume",
        ):
            value = raw.get(key)
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return 0.0

    def _extract_timestamp(self, raw: dict[str, Any]) -> str:
        for key in (
            "updatedAt",
            "updated_at",
            "lastUpdated",
            "last_updated",
            "createdAt",
            "created_at",
        ):
            value = raw.get(key)
            if value:
                return str(value)
        return datetime.now(timezone.utc).isoformat()

    def _extract_markets(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("markets", "data", "results", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def _filter_markets(
        self, markets: list[dict[str, Any]], query: str
    ) -> list[dict[str, Any]]:
        q = query.lower().strip()
        scored: list[tuple[int, dict[str, Any]]] = []
        for market in markets:
            text = " ".join(
                str(market.get(key, ""))
                for key in ("question", "title", "name", "description")
            ).lower()
            if q in text:
                scored.append((0, market))
            elif any(word in text for word in q.split()):
                scored.append((1, market))
        scored.sort(key=lambda item: item[0])
        return [item[1] for item in scored] if scored else markets

    def _get_json(
        self, base_url: str, path: str, params: dict[str, Any] | None = None
    ) -> Any:
        if not self._session:
            raise RuntimeError("requests is not available")

        url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
        response = self._session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "json" in content_type or response.text.strip().startswith(("{", "[")):
            return response.json()
        return response.text

    def _get_cached(self, key: str) -> Any | None:
        with self._cache_lock:
            item = self._cache.get(key)
            if not item:
                return None
            created_at, value = item
            if time.time() - created_at > self.cache_ttl_seconds:
                self._cache.pop(key, None)
                return None
            return value

    def _set_cached(self, key: str, value: Any) -> None:
        with self._cache_lock:
            self._cache[key] = (time.time(), value)

    def _empty_market(self, market_id: str, message: str) -> dict[str, Any]:
        logger.warning("%s", message)
        return {
            "market_id": market_id,
            "question": message,
            "yes_probability": 0.5,
            "no_probability": 0.5,
            "volume_24h": 0.0,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "raw": None,
        }


polymarket_client = PolymarketClient()
