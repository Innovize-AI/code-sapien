import os
import logging
import psycopg
import psycopg.rows

logger = logging.getLogger(__name__)

DB_SCHEMA = os.getenv("DB_SCHEMA", "rfq")


def _get_conn():
    url = os.getenv("DATABASE_URL", "")
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgresql+psycopg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")
    return psycopg.connect(url, connect_timeout=10)


def query_catalog(query: str, top_k: int = 3) -> list[dict]:
    if not query.strip():
        return []
    try:
        conn = _get_conn()
        cur = conn.cursor(row_factory=psycopg.rows.dict_row)
        cur.execute(f"""
            SELECT
                product_id,
                name,
                unit_price,
                available,
                lead_time_days,
                GREATEST(
                    {DB_SCHEMA}.similarity(name, %(q)s::text),
                    {DB_SCHEMA}.similarity(coalesce(description, ''), %(q)s::text),
                    {DB_SCHEMA}.similarity(name || ' ' || coalesce(description, ''), %(q)s::text)
                ) AS score
            FROM {DB_SCHEMA}.products
            WHERE
                available = true
                AND GREATEST(
                    {DB_SCHEMA}.similarity(name, %(q)s::text),
                    {DB_SCHEMA}.similarity(coalesce(description, ''), %(q)s::text),
                    {DB_SCHEMA}.similarity(name || ' ' || coalesce(description, ''), %(q)s::text)
                ) > 0.08
            ORDER BY score DESC
            LIMIT %(k)s
        """, {"q": query, "k": top_k})
        rows = cur.fetchall()
        conn.close()
        return [
            {
                "product_id": row["product_id"],
                "product_name": row["name"],
                "unit_price": float(row["unit_price"]),
                "available": bool(row["available"]),
                "lead_time_days": int(row["lead_time_days"]),
                "score": float(row["score"]),
                "notes": None,
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Catalog query failed: {e}")
        return []


def upsert_product(product: dict):
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.products
                (product_id, name, description, unit_price, available, lead_time_days, category, unit)
            VALUES (%(product_id)s, %(name)s, %(description)s, %(unit_price)s,
                    %(available)s, %(lead_time_days)s, %(category)s, %(unit)s)
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                unit_price = EXCLUDED.unit_price,
                available = EXCLUDED.available,
                lead_time_days = EXCLUDED.lead_time_days,
                category = EXCLUDED.category,
                unit = EXCLUDED.unit
        """, {
            "product_id": product["product_id"],
            "name": product["name"],
            "description": product.get("description", ""),
            "unit_price": float(product["unit_price"]),
            "available": bool(product.get("available", True)),
            "lead_time_days": int(product.get("lead_time_days", 7)),
            "category": product.get("category"),
            "unit": product.get("unit"),
        })
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Upsert product failed: {e}")
        raise


def upsert_products_batch(products: list[dict]):
    if not products:
        return
    conn = _get_conn()
    cur = conn.cursor()
    for p in products:
        cur.execute(f"""
            INSERT INTO {DB_SCHEMA}.products
                (product_id, name, description, unit_price, available, lead_time_days, category, unit)
            VALUES (%(product_id)s, %(name)s, %(description)s, %(unit_price)s,
                    %(available)s, %(lead_time_days)s, %(category)s, %(unit)s)
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                description = EXCLUDED.description,
                unit_price = EXCLUDED.unit_price,
                available = EXCLUDED.available,
                lead_time_days = EXCLUDED.lead_time_days,
                category = EXCLUDED.category,
                unit = EXCLUDED.unit
        """, {
            "product_id": p["product_id"],
            "name": p["name"],
            "description": p.get("description", ""),
            "unit_price": float(p["unit_price"]),
            "available": bool(p.get("available", True)),
            "lead_time_days": int(p.get("lead_time_days", 7)),
            "category": p.get("category"),
            "unit": p.get("unit"),
        })
    conn.commit()
    conn.close()
    logger.info(f"Upserted {len(products)} products into catalog")
