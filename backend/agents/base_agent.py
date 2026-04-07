"""
Abstract base for all analysis agents.
Enforces the FETCH -> BUILD_CONTEXT -> ANALYZE pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json

from backend.llm.budget import BudgetTracker
from backend.llm.prompt_packs import assemble_system_prompt
from backend.llm.provider import get_llm_client
from backend.models.agent_team import CompiledAgentSpec, ExecutionSnapshot
from backend.models.signal import AgentSignal, DataCitation
from backend.security.output_validator import parse_llm_json
from backend.settings.user_settings import DataSourceSettings, LlmSettings


@dataclass
class FetchedData:
    ticker: str
    fetched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    fields: dict = field(default_factory=dict)
    field_sources: dict = field(default_factory=dict)
    field_ages: dict = field(default_factory=dict)
    failed_sources: list[str] = field(default_factory=list)

    def coverage_pct(self, expected: list[str]) -> float:
        if not expected:
            return 0.0
        return len([field for field in expected if self.fields.get(field) is not None]) / len(expected)

    def oldest_age(self) -> float:
        return max(self.field_ages.values(), default=0.0)


ANTI_HALLUCINATION_SUFFIX = """
=== ANALYSIS RULES (strictly enforce) ===
1. Use ONLY data in the DATA CONTEXT above. Do not recall financial figures from memory.
2. For any field marked [NOT AVAILABLE], state explicitly that it cannot be assessed.
3. Every claim in your reasoning must cite the specific data field name that supports it.
4. Do not invent news, earnings, or market conditions not present in the data.
5. If data coverage is low, your confidence must reflect that uncertainty.
6. Output ONLY valid JSON matching the AgentSignal schema. No prose, no markdown.
===========================================
"""


class BaseAnalysisAgent(ABC):
    agent_name: str = "base"
    EXPECTED_FIELDS: list[str] = []

    @abstractmethod
    async def fetch_data(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        compiled_spec: CompiledAgentSpec,
        execution_snapshot: ExecutionSnapshot,
    ) -> FetchedData:
        ...

    @abstractmethod
    def build_system_prompt(self) -> str:
        ...

    @abstractmethod
    def fallback_assessment(
        self,
        ticker: str,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec,
    ) -> tuple[str, float, str]:
        ...

    def build_data_context(
        self,
        data: FetchedData,
        compiled_spec: CompiledAgentSpec | None = None,
        execution_snapshot: ExecutionSnapshot | None = None,
    ) -> str:
        compiled_spec = compiled_spec or self._default_compiled_spec()
        execution_snapshot = execution_snapshot or self._default_execution_snapshot(data.ticker)
        lines = [
            f"TICKER: {data.ticker}",
            f"DATA FETCHED AT: {data.fetched_at}",
            f"BOUNDARY MODE: {execution_snapshot.data_boundary.mode}",
            f"AS OF DATETIME: {execution_snapshot.data_boundary.as_of_datetime or 'live/latest-allowed'}",
            f"PROMPT VARIANT: {compiled_spec.variant_id}",
            f"MODIFIERS: {json.dumps(compiled_spec.modifiers, sort_keys=True)}",
            "",
            "=== DATA CONTEXT ===",
        ]
        for field_name in self.EXPECTED_FIELDS:
            value = data.fields.get(field_name)
            source = data.field_sources.get(field_name, "unknown")
            age = data.field_ages.get(field_name, 0.0)
            if value is None:
                lines.append(f"{field_name}: [NOT AVAILABLE - do not estimate or guess]")
            else:
                lines.append(f"{field_name}: {value} [source: {source}, age: {age:.0f} min]")

        if data.failed_sources:
            lines.append(f"\nFAILED SOURCES: {', '.join(data.failed_sources)}")
            lines.append("Treat any fields from these sources as NOT AVAILABLE.")

        coverage = data.coverage_pct(self.EXPECTED_FIELDS)
        lines.append(f"\nDATA COVERAGE: {coverage*100:.0f}% of expected fields available")
        lines.append("=== END DATA CONTEXT ===")
        return "\n".join(lines)

    def compute_final_confidence(
        self,
        llm_conf: float,
        data: FetchedData,
        max_age: float,
    ) -> tuple[float, str]:
        coverage = data.coverage_pct(self.EXPECTED_FIELDS)
        oldest = data.oldest_age()
        final = llm_conf * coverage
        if oldest > max_age and oldest > 0:
            final *= max_age / oldest
        final = round(max(0.0, min(1.0, final)), 4)
        warning = ""
        if coverage < 0.5:
            warning = f"WARNING: Only {coverage*100:.0f}% of data available. Signal unreliable."
        elif oldest > max_age * 1.5:
            warning = f"WARNING: Data is {oldest:.0f} min old. Signal may be stale."
        return final, warning

    def _build_citations(self, data: FetchedData) -> list[DataCitation]:
        citations: list[DataCitation] = []
        for field_name in self.EXPECTED_FIELDS:
            value = data.fields.get(field_name)
            if value is None:
                continue
            citations.append(
                DataCitation(
                    field_name=field_name,
                    value=str(value),
                    source=data.field_sources.get(field_name, "unknown"),
                    fetched_at=data.fetched_at,
                )
            )
        return citations

    def _fallback_json(self, ticker: str, data: FetchedData, compiled_spec: CompiledAgentSpec) -> str:
        action, raw_confidence, reasoning = self.fallback_assessment(ticker, data, compiled_spec)
        return json.dumps(
            {
                "ticker": ticker.upper(),
                "agent_name": self.agent_name,
                "action": action,
                "raw_confidence": raw_confidence,
                "final_confidence": 0.0,
                "reasoning": reasoning,
                "cited_data": [citation.model_dump() for citation in self._build_citations(data)],
                "unavailable_fields": [],
                "data_coverage_pct": data.coverage_pct(self.EXPECTED_FIELDS),
                "oldest_data_age_minutes": data.oldest_age(),
                "warning": "",
            }
        )

    async def analyze(
        self,
        ticker: str,
        data_settings: DataSourceSettings,
        llm_settings: LlmSettings,
        budget: BudgetTracker,
        compiled_spec: CompiledAgentSpec | None = None,
        execution_snapshot: ExecutionSnapshot | None = None,
    ) -> AgentSignal:
        compiled_spec = compiled_spec or self._default_compiled_spec()
        execution_snapshot = execution_snapshot or self._default_execution_snapshot(ticker)
        data = await self.fetch_data(ticker, data_settings, compiled_spec, execution_snapshot)
        client = get_llm_client(llm_settings)
        raw = self._fallback_json(ticker, data, compiled_spec)
        if client.available:
            try:
                raw = await client.chat(
                    system=self._compose_system_prompt(compiled_spec),
                    messages=[
                        {
                            "role": "user",
                            "content": (
                                f"Analyze {ticker} using ONLY the data context below. "
                                f"Role label: {compiled_spec.modifiers.get('__role_label__', self.agent_name)}. "
                                f"Role description: {compiled_spec.modifiers.get('__role_description__', self.agent_name)}. "
                                f"Return JSON matching AgentSignal schema.\n\n"
                                f"{self.build_data_context(data, compiled_spec, execution_snapshot)}"
                            ),
                        }
                    ],
                    max_tokens=min(800, llm_settings.max_tokens_per_request),
                    temperature=llm_settings.temperature_analysis,
                    budget=budget,
                )
            except Exception:
                raw = self._fallback_json(ticker, data, compiled_spec)

        try:
            signal = parse_llm_json(raw, AgentSignal)
        except ValueError:
            signal = parse_llm_json(self._fallback_json(ticker, data, compiled_spec), AgentSignal)
        signal.agent_name = self.agent_name
        signal.cited_data = self._build_citations(data)
        signal.data_coverage_pct = data.coverage_pct(self.EXPECTED_FIELDS)
        signal.oldest_data_age_minutes = data.oldest_age()
        signal.unavailable_fields = [
            field_name for field_name in self.EXPECTED_FIELDS if data.fields.get(field_name) is None
        ]
        max_age = min(data_settings.max_data_age_minutes, compiled_spec.freshness_limit_minutes)
        signal.final_confidence, signal.warning = self.compute_final_confidence(
            signal.raw_confidence,
            data,
            max_age,
        )
        return signal

    def _compose_system_prompt(self, compiled_spec: CompiledAgentSpec) -> str:
        custom_prompt = str(compiled_spec.modifiers.get("__custom_system_prompt__", "")).strip()
        role_label = str(compiled_spec.modifiers.get("__role_label__", self.agent_name)).strip() or self.agent_name
        role_description = str(compiled_spec.modifiers.get("__role_description__", "")).strip()
        if custom_prompt:
            sections = [
                f"Grounded Analysis Domain: {self.agent_name}",
                f"Custom Role Label: {role_label}",
            ]
            if role_description:
                sections.append(f"Role Description: {role_description}")
            sections.extend(["", "Custom Role Instructions:", custom_prompt])
            allowed_evidence = compiled_spec.modifiers.get("__allowed_evidence__", [])
            if isinstance(allowed_evidence, list) and allowed_evidence:
                sections.extend(["", "Allowed Evidence Bindings:"])
                sections.extend(f"- {item}" for item in allowed_evidence)
            forbidden_rules = compiled_spec.modifiers.get("__forbidden_inference_rules__", [])
            if isinstance(forbidden_rules, list) and forbidden_rules:
                sections.extend(["", "Forbidden Inference Rules:"])
                sections.extend(f"- {item}" for item in forbidden_rules)
            required_output_schema = str(compiled_spec.modifiers.get("__required_output_schema__", "")).strip()
            if required_output_schema:
                sections.extend(["", f"Required Output Schema: {required_output_schema}"])
            operator_notes = str(compiled_spec.modifiers.get("__operator_notes__", "")).strip()
            if operator_notes:
                sections.extend(["", "Operator Notes:", operator_notes])
            return "\n".join(sections) + "\n" + ANTI_HALLUCINATION_SUFFIX

        base = assemble_system_prompt(
            self.agent_name,
            self.build_system_prompt(),
            compiled_spec.variant_id,
            compiled_spec.modifiers,
        )
        custom_sections: list[str] = []
        allowed_evidence = compiled_spec.modifiers.get("__allowed_evidence__", [])
        if isinstance(allowed_evidence, list) and allowed_evidence:
            custom_sections.extend(["", "Allowed Evidence Bindings:"])
            custom_sections.extend(f"- {item}" for item in allowed_evidence)
        forbidden_rules = compiled_spec.modifiers.get("__forbidden_inference_rules__", [])
        if isinstance(forbidden_rules, list) and forbidden_rules:
            custom_sections.extend(["", "Additional Forbidden Inference Rules:"])
            custom_sections.extend(f"- {item}" for item in forbidden_rules)
        return base + ("\n" + "\n".join(custom_sections) if custom_sections else "") + "\n" + ANTI_HALLUCINATION_SUFFIX
    def _default_compiled_spec(self) -> CompiledAgentSpec:
        from backend.agents.registry import AGENT_DATA_DEPS
        from backend.llm.prompt_packs import PROMPT_PACKS_BY_AGENT

        pack = PROMPT_PACKS_BY_AGENT.get(self.agent_name)
        prompt_pack_id = pack.pack_id if pack else f"{self.agent_name}-core"
        prompt_pack_version = pack.version if pack else "1.0.0"
        return CompiledAgentSpec(
            agent_name=self.agent_name,
            enabled=True,
            weight=50,
            prompt_pack_id=prompt_pack_id,
            prompt_pack_version=prompt_pack_version,
            variant_id="balanced",
            modifiers={},
            owned_sources=AGENT_DATA_DEPS.get(self.agent_name, []),
            freshness_limit_minutes=60,
            lookback_config={},
        )

    def _default_execution_snapshot(self, ticker: str) -> ExecutionSnapshot:
        from backend.models.agent_team import CompiledTeam, DataBoundary

        return ExecutionSnapshot(
            mode="analyze",
            created_at=datetime.now(UTC).isoformat(),
            ticker_or_universe=ticker,
            effective_team=CompiledTeam(
                team_id="ephemeral-default",
                name="Ephemeral Default",
                description="Default execution snapshot used for local fallback paths.",
                enabled_agents=[self.agent_name, "risk_manager", "portfolio_manager"],
                agent_weights={self.agent_name: 50},
                compiled_agent_specs={self.agent_name: self._default_compiled_spec()},
                risk_level="moderate",
                time_horizon="medium",
            ),
            provider="fallback",
            model="fallback",
            prompt_pack_versions={},
            settings_hash="fallback",
            team_hash="fallback",
            data_boundary=DataBoundary(mode="live", allow_latest_semantics=True),
            cost_model={},
            notes=["Ephemeral snapshot used by fallback test/helper path."],
        )
