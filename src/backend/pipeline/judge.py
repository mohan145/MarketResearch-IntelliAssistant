import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.backend.pipeline.prompts import render_judge_prompt
from src.backend.pipeline.summarizer import (
    CompetitorActivity,
    Insight,
    MarketSummary,
)

logger = logging.getLogger(__name__)


class JudgeVerdict(BaseModel):
    """Verdict on whether a claim is supported by source material."""

    claim: str = Field(..., description="The claim being evaluated")
    supported: bool = Field(
        ...,
        description="True if claim is supported by source, False if unsupported/contradicted",
    )
    confidence: float = Field(
        ..., description="Confidence in verdict (0.0-1.0)", ge=0.0, le=1.0
    )
    explanation: str = Field(..., description="Detailed reasoning for verdict")
    source_url: str = Field(..., description="URL of the source being checked against")


def check_claim(
    claim: str,
    source_text: str,
    source_url: str,
    llm: BaseChatModel,
    max_retries: int = 1,
) -> JudgeVerdict:
    """Verify a single claim against source material using LLM judge.

    Uses LangChain chain: prompt | llm | JsonOutputParser

    Args:
        claim: The claim to verify
        source_text: Full article text to check against
        source_url: URL of the source
        llm: LLM instance (from get_llm())
        max_retries: Number of retries on JSON parse failure

    Returns:
        JudgeVerdict with supported status and reasoning

    Raises:
        OutputParserException: If JSON parsing fails after retries
    """
    # Render prompt using Jinja2 template
    prompt_text = render_judge_prompt(claim, source_text, source_url)

    # Create LangChain chain: prompt | llm | parser
    prompt = ChatPromptTemplate.from_template(prompt_text)
    parser = JsonOutputParser(pydantic_object=JudgeVerdict)

    chain = prompt | llm | parser

    # Invoke chain with retry logic
    for attempt in range(max_retries + 1):
        try:
            logger.debug(f"Checking claim: {claim[:80]}...")

            result = chain.invoke({})

            # Ensure result is typed JudgeVerdict
            if isinstance(result, dict):
                result = JudgeVerdict(**result)

            # Log verdict
            status = "✅ SUPPORTED" if result.supported else "❌ UNSUPPORTED"
            logger.info(
                f"{status} (confidence {result.confidence:.1%}): {claim[:80]}..."
            )

            return result

        except Exception as e:
            if attempt < max_retries:
                logger.warning(f"Judge attempt {attempt + 1} failed: {e}. Retrying...")

                # Try again with corrective prompt
                corrective_prompt = ChatPromptTemplate.from_template(
                    prompt_text
                    + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                    + "Return ONLY valid JSON, no markdown, no extra text."
                )
                parser = JsonOutputParser(pydantic_object=JudgeVerdict)
                chain = corrective_prompt | llm | parser

            else:
                logger.error(f"Judge failed after {max_retries + 1} attempts")
                raise


def verify_summary(
    summary: MarketSummary,
    source_texts: dict[str, str],
    llm: BaseChatModel,
) -> list[JudgeVerdict]:
    """Verify all claims in a summary against their source materials.

    Iterates through all insights and competitor activities, checking each
    claim against the appropriate source text using the judge LLM.

    Args:
        summary: The market summary to verify
        source_texts: Dict mapping URL → full article text (from ExtractedContent)
        llm: LLM instance (from get_llm())

    Returns:
        List of JudgeVerdicts for all claims checked

    Raises:
        KeyError: If a source URL in summary is not in source_texts dict
    """
    verdicts = []

    # Extract all claims from summary
    claims_to_check = []

    for insight in summary.key_themes:
        for source in insight.sources:
            claims_to_check.append(
                {
                    "claim": insight.finding,
                    "source_url": source.url,
                    "excerpt": source.excerpt,
                }
            )

    for activity in summary.competitor_activities:
        for source in activity.sources:
            claims_to_check.append(
                {
                    "claim": activity.activity,
                    "source_url": source.url,
                    "excerpt": source.excerpt,
                }
            )

    logger.info(f"Verifying {len(claims_to_check)} claims from summary")

    # Check each claim
    for claim_data in claims_to_check:
        claim = claim_data["claim"]
        source_url = claim_data["source_url"]

        if source_url not in source_texts:
            logger.warning(f"Source URL not found: {source_url}. Skipping claim.")
            continue

        source_text = source_texts[source_url]

        try:
            verdict = check_claim(claim, source_text, source_url, llm)
            verdicts.append(verdict)

        except Exception as e:
            logger.error(f"Error checking claim '{claim}': {e}")
            # Continue with next claim rather than failing entirely

    return verdicts


def count_hallucinations(verdicts: list[JudgeVerdict], confidence_threshold: float = 0.7) -> int:
    """Count hallucinations in verdicts.

    A hallucination is: supported=False AND confidence > threshold
    (high-confidence claim that is unsupported)

    Args:
        verdicts: List of JudgeVerdicts from verify_summary()
        confidence_threshold: Minimum confidence to count as hallucination (default 0.7)

    Returns:
        Number of hallucinations found
    """
    hallucinations = [
        v for v in verdicts if not v.supported and v.confidence > confidence_threshold
    ]
    return len(hallucinations)