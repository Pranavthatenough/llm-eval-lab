# Phase 4 - Hallucination testing

**Goal:** catch confident nonsense, and measure it without breaking legitimate answers.

## Concepts

A *hallucination* is output that sounds right and isn't supported by reality or by the provided source. Two kinds matter for testing:

| Kind | Example | How to test |
|---|---|---|
| **Closed-book fabrication** | invents a research paper, API function or statistic | ask about things that *don't exist* (4.1); check self-consistency (4.3) |
| **Grounded / unfaithful** | adds a fact that isn't in the document it was given | break the answer into claims and check each against the context (4.2) |

**Controls are mandatory.** A model that refuses everything never hallucinates and is useless. Every hallucination test needs answerable questions alongside it so you can see over-refusal.

**Faithfulness vs correctness.** Faithful = supported by the given context. Correct = true in the world. For document-grounded apps, faithfulness usually comes first: the document is the source of truth, and if it's wrong, that's a content bug, not a model bug.

**Self-consistency** (the idea behind SelfCheckGPT): when a model knows something, repeated samples agree. When it's guessing, they scatter. This needs no reference answer.

## Exercises

| # | Run | What you'll see |
|---|---|---|
| 4.1 | `python lab.py run 4.1` | 8 questions about invented papers, functions, prizes and drugs + 4 real controls. Abstention scored by keyword heuristic AND judge. |
| 4.2 | `python lab.py run 4.2` | Questions over short documents, some unanswerable. Claim-by-claim faithfulness scoring. |
| 4.3 | `python lab.py run 4.3` | Known vs unknown facts sampled 5x each; agreement rates compared. |

## Reading your results

- **4.1 hallucination rate** = fake questions answered as if real. Report it *together with* accuracy on the real controls.
- **Heuristic vs judge disagreements** are the most educational rows. "I'm not sure, but the paper argues..." contains a refusal phrase *and* a fabrication.
- **4.2 faithfulness** below 1.0 on an answerable question means the model added something. Read the "unsupported claims" line - is the judge right?
- **4.2 unanswerable questions** test whether the model will say "I don't know" when the context *almost* answers. g5 is designed to tempt it.
- **4.3:** lower agreement on unknown questions than known ones is the signal. A consistent "I don't know" is the ideal outcome.

## Break it (challenges)

1. Add a system prompt to 4.1: "If you are not certain something exists, say so." Measure fakes AND controls before/after.
2. Write three fabrication probes about your own domain (a fake internal tool, a fake error code, a fake regulation).
3. In 4.2, edit a context to make a question *almost* answerable, and see if the model bridges the gap.
4. Improve 4.3 by having the judge decide whether two answers mean the same thing instead of exact string matching.

## Real-world notes

- Hallucination rates are task-specific. "3% hallucination" on trivia says nothing about your medical-summary feature. Build probes from your domain.
- Fabricated citations, URLs, function names and numbers are the highest-risk outputs. Deterministic checks (does this URL resolve? does this function exist?) beat judges for them.
