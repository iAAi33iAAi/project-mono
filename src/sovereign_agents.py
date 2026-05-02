"""
SOVEREIGN CO-WORKERS - CrewAI Agent Definitions
PROJECT-MONO | ALGA_FOLD_KERNEL | Node 001
These agents run LOCALLY via Ollama. No data leaves Node 001.
Every agent is governed by the Codex and gated by OpenClaw.
"""

import os
from crewai import Agent, Task, Crew, Process

CODEX_RULES = {
    "non_extraction": "No system may extract value from a human without sovereign consent and equitable return.",
    "human_sovereignty": "Every human maintains irrevocable authority over their digital representation.",
    "lineage_required": "Every action must carry provenance. Anonymous extraction is architecturally impossible.",
}

CODEX_PREAMBLE = (
    "You are a sovereign co-worker under the ALGA_FOLD_KERNEL. "
    "Before EVERY action, verify compliance with three immutable Codex rules: "
    "1) NON-EXTRACTION 2) HUMAN SOVEREIGNTY 3) LINEAGE REQUIRED. "
    "If any action violates these rules, BLOCK it. The system is FAIL-CLOSED."
)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ollama/llama3.2")
OLLAMA_CODE = os.getenv("OLLAMA_CODE_MODEL", "ollama/codellama")
OLLAMA_REASON = os.getenv("OLLAMA_REASON_MODEL", "ollama/mistral")


def create_codex_guardian():
    return Agent(
        role="Codex Guardian",
        goal="Ensure every action complies with the three immutable Codex rules.",
        backstory=f"{CODEX_PREAMBLE} You are the constitutional court of the sovereign architecture.",
        llm=OLLAMA_MODEL,
        verbose=True,
        allow_delegation=False,
    )


def create_research_worker():
    return Agent(
        role="Research Worker",
        goal="Gather and synthesize information with full source attribution and lineage.",
        backstory=f"{CODEX_PREAMBLE} You research topics and present actionable intelligence.",
        llm=OLLAMA_REASON,
        verbose=True,
        allow_delegation=True,
    )


def create_builder():
    return Agent(
        role="Builder",
        goal="Write production-quality code and docs for project-mono.",
        backstory=f"{CODEX_PREAMBLE} You build sovereign infrastructure. Every artifact carries provenance.",
        llm=OLLAMA_CODE,
        verbose=True,
        allow_delegation=True,
    )


def create_colony_manager():
    return Agent(
        role="Colony Manager",
        goal="Monitor Colony health, spawn replacements, provision workers. MAPE loop.",
        backstory=f"{CODEX_PREAMBLE} You manage the Grapple Colony execution layer.",
        llm=OLLAMA_MODEL,
        verbose=True,
        allow_delegation=True,
    )


def deploy_colony(tasks=None, process="sequential"):
    guardian = create_codex_guardian()
    researcher = create_research_worker()
    builder = create_builder()
    manager = create_colony_manager()
    if tasks is None:
        tasks = [
            Task(
                description="Index the Biomanifesto and all repo docs into ChromaDB with lineage.",
                expected_output="Structured indexing report.",
                agent=researcher,
            ),
            Task(
                description="Propose up to 5 new Codex rules from the Biomanifesto. PROPOSALS ONLY.",
                expected_output="List of proposed rules pending Architect approval.",
                agent=guardian,
            ),
            Task(
                description="Write active_digitwin.py implementing Mode 2 delegation with full lineage.",
                expected_output="Complete Python source for active_digitwin.py.",
                agent=builder,
            ),
        ]
    colony = Crew(
        agents=[guardian, researcher, builder, manager],
        tasks=tasks,
        process=Process.sequential if process == "sequential" else Process.hierarchical,
        verbose=True,
        memory=True,
    )
    print("[COLONY] Sovereign co-workers deployed.")
    print("[CODEX] Three immutable rules loaded.")
    print("[OPENCLAW] Governance gate ACTIVE, fail-closed.")
    return str(colony.kickoff())


if __name__ == "__main__":
    print("PROJECT-MONO | Sovereign Co-Worker Deployment")
    print("ALGA_FOLD_KERNEL | Node 001 | Bethel Acres, OK")
    deploy_colony()
