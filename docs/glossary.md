# Glossary

**Abstention** - the model declining to answer or saying it doesn't know. Good on unanswerable questions; bad (over-refusal) on answerable ones.

**Agent** - a model running in a loop that chooses actions (tool calls) and observes their results until it finishes a task.

**ASR (Attack Success Rate)** - successful attacks / attacks attempted.

**Canary token** - a unique secret string planted in a prompt or document; if it appears in output, something leaked.

**Chunk** - a piece of a document stored for retrieval in RAG.

**Composite score** - several metrics combined with weights into one number.

**Confidence interval (CI)** - the range a true rate plausibly falls in given your sample size. The lab prints 95% Wilson intervals.

**Context window** - the maximum amount of text (in tokens) the model can consider at once. In Ollama, set by `num_ctx`.

**Deterministic check** - a plain-code assertion on output (regex, contains, schema). Same input, same verdict, every time.

**Embedding** - a list of numbers representing a text's meaning; similar texts get similar vectors. Used for semantic search.

**Faithfulness** - whether every claim in an answer is supported by the provided context.

**Flaky case** - a case that sometimes passes and sometimes fails with no change to code or data.

**Golden set** - a curated dataset of inputs with expected outputs/properties, used for regression testing.

**Grounding** - giving the model source material (documents, tool results) and asking it to answer from that.

**Hallucination** - fluent output not supported by reality or by the provided source.

**hit@k** - whether at least one relevant document appears in the top k retrieval results.

**Indirect prompt injection** - malicious instructions hidden in content the app feeds to the model (emails, web pages, retrieved docs).

**LLM-as-a-judge** - using a model to grade another model's output against a rubric.

**MRR (Mean Reciprocal Rank)** - average of 1/rank of the first relevant result (1 = always first).

**Ollama** - a tool for downloading and running open models locally behind an HTTP API.

**Over-refusal** - refusing legitimate, harmless requests.

**Pairwise judging** - asking a judge which of two answers is better, rather than scoring one alone.

**Position bias** - a judge preferring an answer because of where it appears (first or second).

**Prompt injection** - input that causes the model to follow an attacker's instructions instead of the application's.

**RAG (Retrieval-Augmented Generation)** - retrieve relevant documents, then generate an answer from them.

**recall@k** - the fraction of all relevant documents that appear in the top k retrieval results.

**Reference answer** - an expert-written correct answer used by checks or judges for comparison.

**Rubric** - written definitions of what each score level means.

**Seed** - a number that fixes the random sampling sequence, making outputs more repeatable.

**Self-consistency** - agreement among several sampled answers to the same question; low agreement suggests guessing.

**Structured output** - constraining model output to a JSON schema.

**System prompt** - the application's instructions to the model, usually hidden from users.

**Temperature** - controls sampling randomness. 0 = most likely tokens; higher = more varied.

**Token** - the unit models read and write; roughly 3/4 of an English word on average.

**Trajectory** - the full sequence of actions an agent took, including tool calls and arguments.

**Verbosity bias** - a judge preferring longer answers regardless of correctness.
