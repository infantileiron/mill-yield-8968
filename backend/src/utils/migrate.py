from sqlalchemy import text,inspect
def ensure_review_columns(engine):
    with engine.begin() as c:
        cols={x['name'] for x in inspect(c).get_columns('reviews')}
        if 'source' not in cols:c.execute(text("ALTER TABLE reviews ADD COLUMN source VARCHAR(10) DEFAULT 'ledger'"))
        if 'source_meta' not in cols:c.execute(text("ALTER TABLE reviews ADD COLUMN source_meta JSON"))
        c.execute(text("UPDATE reviews SET source='ledger' WHERE source IS NULL"))
