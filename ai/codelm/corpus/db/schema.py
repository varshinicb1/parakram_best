"""SQLAlchemy ORM — the corpus schema."""

from sqlalchemy import Column, Integer, String, Boolean, Float, Text, JSON, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DB_PATH

Base = declarative_base()


class Block(Base):
    """A verified code block in the corpus."""
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    block_id = Column(String(64), unique=True, nullable=False, index=True)
    function_name = Column(String(256), nullable=False)
    signature = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    source_repo = Column(String(128), nullable=False)
    source_file = Column(String(512), nullable=False)
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    line_count = Column(Integer, nullable=False)
    license = Column(String(64), nullable=False)

    # Correctness
    compiles_clean = Column(Boolean, default=False)
    warnings_count = Column(Integer, default=0)
    ubsan_clean = Column(Boolean, default=False)
    stack_cost_bytes = Column(Integer, nullable=True)

    # Semantics
    tags = Column(JSON, default=list)
    peripherals = Column(JSON, default=list)
    target_mcus = Column(JSON, default=list)
    includes = Column(JSON, default=list)
    calls = Column(JSON, default=list)

    # Embedding
    embedding_blob = Column(Text, nullable=True)


class CorpusStats(Base):
    """Aggregate corpus statistics."""
    __tablename__ = "corpus_stats"

    id = Column(Integer, primary_key=True)
    total_blocks = Column(Integer, default=0)
    valid_blocks = Column(Integer, default=0)
    total_repos = Column(Integer, default=0)
    avg_block_lines = Column(Float, default=0.0)
    last_updated = Column(String(32))


def get_engine():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{DB_PATH}", echo=False)


def get_session():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()
