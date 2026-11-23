"""Agent routing with a controlled model stand-in."""

import pytest

from agentic_rag import agents
from agentic_rag.config import Settings
from agentic_rag.vector_store import Evidence


class FakeStore:
    def search(self, query, limit):
        return [Evidence("guide.txt", 0, "The incident commander leads.", 0.1)]


@pytest.mark.asyncio
async def test_routed_answer_includes_evidence(monkeypatch):
    prompts = []

    async def stub(prompt, instruction, settings):
        prompts.append(prompt)
        if len(prompts) == 1:
            return agents.AgentResult("DOCUMENT", 8)
        return agents.AgentResult("The incident commander leads [S1].", 12)

    monkeypatch.setattr(agents, "run_adk", stub)
    result = await agents.AgentPipeline(Settings(), FakeStore()).ask(
        "Who leads the incident?"
    )
    assert result["route"] == "retrieval"
    assert result["sources"][0]["id"] == "S1"
    assert result["tokens"] == 20
    assert "incident commander" in result["answer"]


@pytest.mark.asyncio
async def test_router_defaults_to_retrieval(monkeypatch):
    async def stub(prompt, instruction, settings):
        return agents.AgentResult("Not sure", None)

    monkeypatch.setattr(agents, "run_adk", stub)
    result = await agents.AgentPipeline(Settings(), FakeStore()).ask("Policy?")
    assert result["route"] == "retrieval"
