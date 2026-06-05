"""Pravah autonomous control loop.

Continuously:
  1. Reads active deployments from Shivam's registry
  2. Fetches telemetry from Shivam's monitoring layer
  3. Runs decision pipeline
  4. Orchestrator executes
  5. Learning feedback applied

No parallel monitoring loops, no alternate telemetry pipelines.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from .action_scope import ActionGuard
from .orchestrator import OrchestratorClient
from .pipeline import DecisionPipeline
from .rl_engine import DecisionGenerator
from .state import AppStateStore
from .telemetry import DeploymentRegistry, TelemetryClient

logger = logging.getLogger(__name__)


class PravahOrganismLoop:
    """The unified Pravah organism — brain wired to body."""

    def __init__(
        self,
        telemetry: TelemetryClient,
        registry: DeploymentRegistry,
        orchestrator: OrchestratorClient,
        poll_interval: float = 10.0,
        cooldown_seconds: float = 15.0,
    ):
        self._telemetry = telemetry
        self._registry  = registry
        self._interval  = poll_interval

        store     = AppStateStore(cooldown_seconds=cooldown_seconds)
        guard     = ActionGuard()
        generator = DecisionGenerator(enable_rl=True)

        self._pipeline = DecisionPipeline(
            orchestrator=orchestrator,
            guard=guard,
            store=store,
            generator=generator,
            enable_learning=True,
        )
        self._store = store

    def tick(self):
        """Single reconciliation tick across all registered deployments."""
        deployments = self._registry.list_active()
        if not deployments:
            logger.debug("[LOOP] no active deployments")
            return

        for dep in deployments:
            dep_id = dep.get("deployment_id") or dep.get("id")
            if not dep_id:
                continue

            payload = self._telemetry.fetch(dep_id)
            if payload is None:
                logger.warning("[LOOP] no telemetry for deployment=%s", dep_id)
                continue

            self._pipeline.process(payload)

        self._store.gc()

    def run(self, max_ticks: Optional[int] = None):
        """Run the control loop. max_ticks=None means run forever."""
        logger.info("[PRAVAH] organism loop started (interval=%.1fs)", self._interval)
        ticks = 0
        while max_ticks is None or ticks < max_ticks:
            try:
                self.tick()
            except Exception as exc:
                logger.error("[PRAVAH] tick error: %s", exc)
            ticks += 1
            if max_ticks is None or ticks < max_ticks:
                time.sleep(self._interval)
        logger.info("[PRAVAH] organism loop finished after %d ticks", ticks)
