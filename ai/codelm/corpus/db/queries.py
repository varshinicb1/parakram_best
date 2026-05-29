"""All corpus queries in one place."""

from sqlalchemy import func

from corpus.db.schema import Block, CorpusStats, get_session


def count_blocks() -> int:
    session = get_session()
    return session.query(func.count(Block.id)).scalar() or 0


def count_valid_blocks() -> int:
    session = get_session()
    return session.query(func.count(Block.id)).filter(Block.compiles_clean == True).scalar() or 0


def get_blocks_by_tag(tag: str, limit: int = 100) -> list[Block]:
    session = get_session()
    return session.query(Block).filter(Block.tags.contains(tag)).limit(limit).all()


def get_blocks_by_peripheral(peripheral: str, limit: int = 100) -> list[Block]:
    session = get_session()
    return session.query(Block).filter(Block.peripherals.contains(peripheral)).limit(limit).all()


def get_blocks_by_mcu(mcu: str, limit: int = 100) -> list[Block]:
    session = get_session()
    return session.query(Block).filter(Block.target_mcus.contains(mcu)).limit(limit).all()


def search_blocks(query: str, limit: int = 50) -> list[Block]:
    session = get_session()
    pattern = f"%{query}%"
    return session.query(Block).filter(
        (Block.function_name.like(pattern)) |
        (Block.signature.like(pattern))
    ).limit(limit).all()


def update_corpus_stats() -> CorpusStats:
    session = get_session()
    stats = session.query(CorpusStats).first()
    if not stats:
        stats = CorpusStats(id=1)
        session.add(stats)

    stats.total_blocks = count_blocks()
    stats.valid_blocks = count_valid_blocks()

    avg = session.query(func.avg(Block.line_count)).scalar()
    stats.avg_block_lines = float(avg) if avg else 0.0

    from datetime import datetime
    stats.last_updated = datetime.utcnow().isoformat()

    session.commit()
    return stats
