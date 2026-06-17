import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.backend.database import Base


@pytest.fixture
def test_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    yield SessionLocal()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_html():
    """Sample HTML fixture for scraper tests."""
    return """
    <html>
      <head><title>Sample Article</title></head>
      <body>
        <article>
          <h1>AI Market Trends 2024</h1>
          <p>The AI market is experiencing rapid growth and transformation across multiple sectors.
          OpenAI launched GPT-4o with significantly improved capabilities and performance metrics.
          Mistral AI released an open-source model that competes directly with proprietary solutions.
          Enterprises worldwide are adopting AI at unprecedented scale and speed.</p>
          <p>Key themes include major pricing changes, open-source model availability, and widespread enterprise adoption.
          These represent the most significant shifts in the AI landscape this year.
          Industry analysts predict continued acceleration in AI deployment and innovation across all sectors.</p>
        </article>
      </body>
    </html>
    """