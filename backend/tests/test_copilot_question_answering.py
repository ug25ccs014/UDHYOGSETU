"""Answers must depend on the question asked (intent routing, section chunking, extractive fallback)."""

import asyncio

from app.ai.llm_provider import MockLLMProvider
from app.rag.pipeline import RAGPipeline, _expand_query_stems, _stems
from app.workflows.copilot_workflow import CopilotWorkflow

DOC = """# Boiler Registration (Maharashtra)

Every steam boiler must be registered before it is put into use.

## Documents required

- Certificate of manufacture from the boiler manufacturer
- Hydraulic test certificate performed before installation

## Typical timeline

Initial inspection and registration is normally completed within 45 to 60 days from submission of a complete application.
"""


def test_intent_uses_whole_words_and_personal_cues():
    wf = CopilotWorkflow(None)
    # "act" inside "factory" must not trigger anything odd; "how long" about a regulation is not a status query.
    assert wf.detect_intent("How long does MPCB consent take?") == "regulation"
    assert wf.detect_intent("Tell me about factory licensing process") == "regulation"
    assert wf.detect_intent("What documents are required for boiler registration?") == "regulation"
    assert wf.detect_intent("Is my uploaded PAN document valid?") == "document"
    assert wf.detect_intent("Which subsidy schemes am I eligible for?") == "scheme"
    assert wf.detect_intent("Where is my application status?") == "status"


def test_markdown_is_chunked_by_section_with_labels():
    chunks = RAGPipeline(None)._chunk_text(DOC, 500, 50)
    labels = [c.splitlines()[0] for c in chunks]
    assert "Boiler Registration (Maharashtra) › Documents required" in labels
    assert "Boiler Registration (Maharashtra) › Typical timeline" in labels


def test_query_stems_ignore_stopwords_and_punctuation():
    assert _stems("What is the boiler unit?") == {"boiler", "unit"}
    assert "timeline" in _expand_query_stems("How long does it take?")


def _answer(question):
    pipe = RAGPipeline(None)
    chunks = pipe._chunk_text(DOC, 500, 50)
    q = _stems(question)
    bonus = _expand_query_stems(question)
    ranked = sorted(
        chunks,
        key=lambda c: len(q & _stems(c)) / len(q) + 0.15 * len(bonus & _stems(c)),
        reverse=True,
    )
    prompt = pipe.construct_prompt(question, [{"text": c} for c in ranked[:2]])
    return asyncio.run(MockLLMProvider().generate("sys", prompt))


def test_offline_answer_follows_the_question():
    assert "45 to 60 days" in _answer("How long does boiler registration take?")
    docs = _answer("What documents are required for boiler registration?")
    assert "Hydraulic test certificate" in docs and "45 to 60 days" not in docs
