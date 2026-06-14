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
          <p>The AI market is experiencing rapid growth. OpenAI launched GPT-4o with improved capabilities.
          Mistral AI released an open-source model. Enterprises are adopting AI at scale.</p>
          <p>Key themes include pricing changes, open-source models, and enterprise adoption.
          These represent the major shifts in the AI landscape.</p>
        </article>
      </body>
    </html>
    """