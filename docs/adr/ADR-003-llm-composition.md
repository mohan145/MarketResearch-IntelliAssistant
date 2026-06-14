# ADR-003: LLM Layer Design (Composition over Inheritance)

**Date:** 2026-06-13  
**Status:** Accepted  
**Author:** Claude + Mohan Krishna Kosetti

---

## Problem

We need an LLM layer that:
1. Defaults to Google Gemini (free tier)
2. Can swap to Anthropic Claude or OpenAI GPT by config change only
3. Uses the same business logic (summarizer, judge) regardless of LLM provider
4. Doesn't require code changes to add new LLM providers

---

## Options Considered

### Option 1: Composition + Dependency Injection (Chosen)
- **Approach:** Factory function returns `BaseChatModel` from LangChain
- **Injection:** Pass LLM instance to functions, not subclass them
- **Pattern:** `prompt | llm | parser`

**Pros:**
- Zero code changes to swap providers (config only)
- Single business logic, multiple LLM backends
- Easy to test (mock `llm` parameter)
- Clean separation: LLM handling vs business logic
- Scales to new providers without refactoring

**Cons:**
- Requires understanding of dependency injection
- LangChain dependency (but it's standard)

### Option 2: Inheritance (Rejected)
- **Approach:** Subclass `BaseLLM` for each provider
- **Pattern:** `class GoogleLLM(BaseLLM): def summarize()`

**Pros:**
- Familiar OOP pattern
- Type hints are automatic

**Cons:**
- To swap providers, rewrite entire class
- Duplicates business logic across classes
- Hard to test (can't inject different LLM)
- Breaks single-responsibility principle

### Option 3: Strategy Pattern (Hybrid)
- **Approach:** Define interface, implement per provider
- **Pattern:** Similar to composition but more explicit

**Pros:**
- Clear interface

**Cons:**
- More boilerplate than composition
- Same benefits as inheritance approach

---

## Decision

**Use Composition + LangChain's `BaseChatModel`.**

### Architecture

```
src/backend/pipeline/llm.py

├── get_llm(provider: str) -> BaseChatModel
│   └── Returns ChatGoogleGenerativeAI | ChatAnthropic | ChatOpenAI
│
├── summarize(content, competitors, topics, llm: BaseChatModel) -> MarketSummary
│   └── Uses: prompt | llm | JsonOutputParser
│
└── verify_summary(summary, source_text, llm: BaseChatModel) -> list[JudgeVerdict]
    └── Uses: prompt | llm | JsonOutputParser
```

### Factory Function

```python
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel

def get_llm(provider: str | None = None) -> BaseChatModel:
    """Get LLM instance by provider name."""
    provider = provider or settings.llm_provider
    
    providers = {
        "google": lambda: ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            api_key=settings.google_api_key,
            temperature=0.7,
        ),
        "anthropic": lambda: ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=settings.anthropic_api_key,
            temperature=0.7,
        ),
        "openai": lambda: ChatOpenAI(
            model="gpt-4o-mini",
            api_key=settings.openai_api_key,
            temperature=0.7,
        ),
    }
    
    if provider not in providers:
        raise ValueError(f"Unknown LLM provider: {provider}")
    
    return providers[provider]()
```

### LangChain Chain Pattern

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel

class MarketSummary(BaseModel):
    executive_summary: str
    key_themes: list[Insight]
    competitor_activities: list[CompetitorActivity]

def summarize(
    content: list[ExtractedContent],
    competitors: list[str],
    topics: list[str],
    llm: BaseChatModel,
) -> MarketSummary:
    """Summarize market research using LLM chain."""
    
    prompt = ChatPromptTemplate.from_template(SUMMARIZE_PROMPT_TEMPLATE)
    parser = JsonOutputParser(pydantic_object=MarketSummary)
    
    chain = prompt | llm | parser
    
    result = chain.invoke({
        "competitors": ", ".join(competitors),
        "topics": ", ".join(topics),
        "content": content,
    })
    
    return MarketSummary(**result)  # Type-safe
```

### Swapping Providers (no code change)

```python
# In .env or config:
LLM_PROVIDER=anthropic  # Was: google

# In code (no changes needed):
llm = get_llm()  # Now returns ChatAnthropic automatically
result = summarize(content, competitors, topics, llm)  # Same call
```

---

## Rationale

1. **Pluggable:** Config change swaps LLM, zero code edits
2. **Testable:** Mock `llm` param for unit tests
3. **Scalable:** Add new provider by adding one dict entry in `get_llm()`
4. **Standard:** LangChain is the de-facto standard for LLM chains in Python
5. **Future-proof:** Easy to add local models (Ollama, llama.cpp) later

---

## Prompt Management

Prompts stored as Jinja2 templates in `src/backend/pipeline/prompts/`:

```
prompts/
├── summarize.j2
├── judge.j2
└── research.j2
```

**Why Jinja2:**
- Separate concerns (prompt text vs code)
- Version control prompts independently
- Share templates across providers (same prompt works for Google/Anthropic/OpenAI)
- Easy A/B testing

---

## Output Parsing

Use Pydantic models + `JsonOutputParser`:

```python
# Define schema
class Insight(BaseModel):
    theme: str
    finding: str
    sources: list[SourceRef]

# Parse JSON from LLM
parser = JsonOutputParser(pydantic_object=Insight)
chain = prompt | llm | parser

# Result is typed Insight, not raw dict
result: Insight = chain.invoke(...)
```

**Benefits:**
- Type safety
- Validation on LLM output (rejects malformed JSON)
- IDE autocomplete

---

## Retry & Error Handling

LangChain chains don't auto-retry JSON parse failures. We'll add:

```python
def summarize_with_retry(content, competitors, topics, llm, max_retries=1):
    """Summarize with automatic retry on JSON parse failure."""
    for attempt in range(max_retries + 1):
        try:
            return summarize(content, competitors, topics, llm)
        except OutputParserException as e:
            if attempt < max_retries:
                logger.warning(f"Parse failed, retrying: {e}")
                # Add corrective prompt: "Return valid JSON only"
            else:
                raise
```

---

## Future Extensibility

### Local Models (Phase 7+)
```python
# Add Ollama support
from langchain_community.llms import Ollama

providers["ollama"] = lambda: Ollama(
    model="llama2",
    base_url="http://localhost:11434",
)
```

### Custom Reasoning (Phase 8+)
```python
# Use Claude with extended thinking
ChatAnthropic(
    model="claude-opus-4-7",
    thinking={
        "type": "enabled",
        "budget_tokens": 10000,
    },
)
```

### Streaming (Phase 9+)
```python
# Stream results for real-time UI updates
for chunk in llm.stream(...):
    yield chunk
```

---

## References
- LangChain documentation: https://python.langchain.com/docs/
- LangChain composition: https://python.langchain.com/docs/expression_language/
- Pydantic JSON parsing: https://docs.pydantic.dev/