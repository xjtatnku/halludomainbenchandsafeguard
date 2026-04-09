from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .config import GuardConfig
from .extractors import extract_candidates
from .policy import classify_candidate
from .truth_store import TruthStore
from .utils import read_json, read_jsonl, write_json, write_jsonl
from .verifier import verify_candidate


INTENT_TO_ENTRY_TYPES = {
    "login_entry": ["login"],
    "payment_entry": ["payment"],
    "download_entry": ["download"],
    "support_entry": ["support"],
    "official_entry": ["homepage"],
    "resource_navigation": ["docs"],
}


class SafeEntryGuard:
    def __init__(self, config: GuardConfig):
        self.config = config
        self.truth_store = TruthStore.load(config.truth_store_path)

    def inspect_truth(self) -> dict[str, Any]:
        return self.truth_store.summarize()

    def _resolve_requested_entry_types(
        self,
        *,
        prompt: str,
        explicit_entry_types: list[str] | None = None,
        intent: str = "",
    ) -> list[str]:
        if explicit_entry_types:
            return self.truth_store.infer_requested_entry_types(prompt, explicit_entry_types)
        if intent in INTENT_TO_ENTRY_TYPES:
            return list(INTENT_TO_ENTRY_TYPES[intent])
        return self.truth_store.infer_requested_entry_types(prompt, explicit_entry_types)

    def _resolve_prompt_context(self, row: dict[str, Any], prompt_map: dict[str, dict[str, Any]]) -> dict[str, Any]:
        prompt_record = prompt_map.get(str(row.get("prompt_id", "")), {})
        meta = dict(row.get("meta") or {})
        prompt_text = str(prompt_record.get("prompt") or row.get("prompt") or meta.get("prompt") or "")
        expected_entity = str(
            prompt_record.get("expected_entity")
            or row.get("expected_entity")
            or meta.get("expected_entity")
            or ""
        )
        expected_entry_types = list(
            prompt_record.get("expected_entry_types")
            or row.get("expected_entry_types")
            or meta.get("expected_entry_types")
            or []
        )
        intent = str(prompt_record.get("intent") or meta.get("intent") or row.get("intent") or "")
        return {
            "prompt_record": prompt_record,
            "meta": meta,
            "prompt": prompt_text,
            "expected_entity": expected_entity,
            "expected_entry_types": expected_entry_types,
            "intent": intent,
            "life_domain": str(prompt_record.get("life_domain") or meta.get("life_domain") or ""),
            "risk_tier": str(prompt_record.get("risk_tier") or meta.get("risk_tier") or ""),
            "language": str(prompt_record.get("language") or meta.get("language") or ""),
        }

    def _make_summary(self, filtered_rows: list[dict[str, Any]], input_path: str | Path = "") -> dict[str, Any]:
        label_counts: dict[str, int] = {}
        model_counts: dict[str, dict[str, int]] = {}
        for row in filtered_rows:
            label = str(row.get("recommended_label") or "rejected")
            label_counts[label] = label_counts.get(label, 0) + 1
            model = str(row.get("model") or "unknown")
            if model not in model_counts:
                model_counts[model] = {"accepted": 0, "rejected": 0}
            if row.get("rejected"):
                model_counts[model]["rejected"] += 1
            else:
                model_counts[model]["accepted"] += 1
        row_count = len(filtered_rows)
        accepted_count = sum(1 for row in filtered_rows if not row["rejected"])
        rejected_count = row_count - accepted_count
        return {
            "input_path": str(Path(input_path)) if input_path else "",
            "row_count": row_count,
            "accepted_count": accepted_count,
            "rejected_count": rejected_count,
            "accept_rate": round(accepted_count / row_count, 4) if row_count else 0.0,
            "label_counts": label_counts,
            "model_counts": model_counts,
        }

    def filter_answer(
        self,
        *,
        prompt: str,
        response: str,
        expected_entity: str = "",
        requested_entry_types: list[str] | None = None,
        intent: str = "",
        prompt_id: str = "",
        model: str = "",
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entity_inference = self.truth_store.infer_entity(prompt, explicit_entity=expected_entity)
        entity = self.truth_store.find_entity(entity_inference.entity_id) if entity_inference else None
        requested_types = self._resolve_requested_entry_types(
            prompt=prompt,
            explicit_entry_types=requested_entry_types,
            intent=intent,
        )
        candidates = extract_candidates(response)

        candidate_rows: list[dict[str, Any]] = []
        for candidate in candidates:
            verification_row = verify_candidate(
                candidate.normalized_url,
                verification=self.config.verification,
                official_domains=(entity.official_domains if entity else []),
            )
            match = self.truth_store.match_candidate(candidate.normalized_url, entity, requested_types)
            decision = classify_candidate(
                candidate,
                verification_row,
                match,
                requested_entry_types=requested_types,
                entity_detected=entity is not None,
                policy=self.config.policy,
            )
            candidate_rows.append(
                {
                    "candidate": asdict(candidate),
                    "verification": verification_row,
                    "match": asdict(match),
                    "decision": decision,
                }
            )

        candidate_rows.sort(
            key=lambda row: (
                row["decision"]["can_recommend"],
                row["decision"]["recommendation_score"],
                -row["candidate"]["position"],
            ),
            reverse=True,
        )
        recommended = next((row for row in candidate_rows if row["decision"]["can_recommend"]), None)
        if not candidate_rows:
            filtered_text = "No URL or domain was extracted from the model answer."
            rejection_reason = "no_candidates_extracted"
        elif recommended is None:
            filtered_text = "No sufficiently safe and verified domain was found in the model answer. Do not click the returned links directly."
            rejection_reason = "all_candidates_blocked"
        else:
            filtered_text = f"Recommended safe link: {recommended['candidate']['normalized_url']}"
            rejection_reason = ""
        safe_candidates = [row for row in candidate_rows if row["decision"]["can_recommend"]]
        blocked_candidates = [row for row in candidate_rows if not row["decision"]["can_recommend"]]
        return {
            "status": "accepted" if recommended else "rejected",
            "prompt_id": prompt_id,
            "model": model,
            "prompt": prompt,
            "response": response,
            "inferred_entity": asdict(entity_inference) if entity_inference else None,
            "requested_entry_types": requested_types,
            "candidate_count": len(candidate_rows),
            "safe_candidate_count": len(safe_candidates),
            "blocked_candidate_count": len(blocked_candidates),
            "recommended": recommended,
            "recommended_url": recommended["candidate"]["normalized_url"] if recommended else "",
            "recommended_label": recommended["decision"]["risk_label"] if recommended else "rejected",
            "recommended_score": recommended["decision"]["recommendation_score"] if recommended else 0.0,
            "rejected": recommended is None,
            "rejection_reason": rejection_reason,
            "filtered_text": filtered_text,
            "context": context or {},
            "candidates": candidate_rows,
        }

    def filter_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        dataset_path: str | Path | None = None,
        limit: int = 0,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        prompt_map: dict[str, dict[str, Any]] = {}
        if dataset_path:
            dataset_payload = read_json(dataset_path)
            records = dataset_payload.get("records", []) if isinstance(dataset_payload, dict) else []
            prompt_map = {str(record.get("prompt_id", "")): record for record in records}

        filtered_rows: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            if limit > 0 and index > limit:
                break
            context = self._resolve_prompt_context(row, prompt_map)
            result = self.filter_answer(
                prompt=context["prompt"],
                response=str(row.get("response") or ""),
                expected_entity=context["expected_entity"],
                requested_entry_types=context["expected_entry_types"],
                intent=context["intent"],
                prompt_id=str(row.get("prompt_id", "")),
                model=str(row.get("model", "")),
                context={
                    "intent": context["intent"],
                    "life_domain": context["life_domain"],
                    "risk_tier": context["risk_tier"],
                    "language": context["language"],
                },
            )
            filtered_rows.append(
                {
                    "model": row.get("model", ""),
                    "prompt_id": row.get("prompt_id", ""),
                    "recommended_url": result["recommended_url"],
                    "recommended_label": result["recommended_label"],
                    "recommended_score": result["recommended_score"],
                    "candidate_count": result["candidate_count"],
                    "safe_candidate_count": result["safe_candidate_count"],
                    "blocked_candidate_count": result["blocked_candidate_count"],
                    "rejected": result["rejected"],
                    "rejection_reason": result["rejection_reason"],
                    "filtered_text": result["filtered_text"],
                    "detail": result,
                }
            )
        return filtered_rows, self._make_summary(filtered_rows)

    def filter_jsonl(
        self,
        *,
        input_path: str | Path,
        output_path: str | Path,
        dataset_path: str | Path | None = None,
        summary_path: str | Path | None = None,
        limit: int = 0,
    ) -> dict[str, Any]:
        rows = read_jsonl(input_path)
        filtered_rows, summary = self.filter_rows(rows, dataset_path=dataset_path, limit=limit)
        write_jsonl(output_path, filtered_rows)
        summary["input_path"] = str(Path(input_path))
        summary["output_path"] = str(Path(output_path))
        if summary_path:
            write_json(summary_path, summary)
        return summary
