from __future__ import annotations

import re

from foundry.schemas.safety import RiskAssessment


class SafetyChecker:
    SECRET_FILE_NAMES = {".env", ".env.local", ".env.production"}
    SECRET_FILE_PARTS = {"secrets", "private_keys", "wallets"}

    def scan(
        self,
        *,
        task_id: str,
        actor_agent: str,
        changed_files: list[str],
        diff_text: str,
        project_type: str,
    ) -> RiskAssessment:
        reasons: list[str] = []
        lowered_diff = diff_text.lower()
        lowered_files = [path.lower() for path in changed_files]

        if any(path in self.SECRET_FILE_NAMES for path in lowered_files) or any(
            part in path.split("/") for path in lowered_files for part in self.SECRET_FILE_PARTS
        ):
            reasons.append("secret-file")

        if "private key" in lowered_diff or "private_key" in lowered_diff:
            reasons.append("private-key")
        if "seed phrase" in lowered_diff or "mnemonic" in lowered_diff:
            reasons.append("seed-phrase")
        if "danger-full-access" in lowered_diff or "--yolo" in lowered_diff:
            reasons.append("danger-full-access")
        if re.search(r"rm\s+-rf\s+/", lowered_diff):
            reasons.append("destructive-command")
        if actor_agent == "builder" and any(path.startswith("policies/") for path in lowered_files):
            reasons.append("builder-policy-edit")

        if project_type == "trading-research":
            if "live_trading = true" in lowered_diff or "allow_live" in lowered_diff:
                reasons.append("live-trading")
            if "signtransaction" in lowered_diff or "wallet signing" in lowered_diff:
                reasons.append("wallet-signing")
            if "broker execute" in lowered_diff or "/execute" in lowered_diff:
                reasons.append("broker-execution")
            if "leverage" in lowered_diff and "default" in lowered_diff:
                reasons.append("leverage-default")

        reasons = sorted(set(reasons))
        return RiskAssessment(
            task_id=task_id,
            approved=not reasons,
            risk_level="critical" if reasons else "low",
            blocked_reasons=reasons,
            mitigations_required=["Resolve blocked safety findings."] if reasons else [],
        )
