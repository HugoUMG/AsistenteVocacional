"""Costo por sesion de las ultimas 24 horas, con el total al final.

    uv run python gasto_24h.py            # usa DATABASE_URL de backend/.env
    uv run python gasto_24h.py 72         # otra ventana, en horas

Los precios salen de recomendar.PRECIO_USD_POR_1M, asi no hay dos tablas de
precios que se desincronicen. Sesiones sin billing: es "lo que habria costado".
"""
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import UsoTokens
from app.recomendar import costo_usd

horas = float(sys.argv[1]) if len(sys.argv) > 1 else 24

with SessionLocal() as db:
    filas = db.execute(
        select(
            UsoTokens.session_id,
            func.min(UsoTokens.created_at),
            func.count(),
            func.sum(UsoTokens.prompt_tokens),
            func.sum(UsoTokens.cached_tokens),
            func.sum(UsoTokens.output_tokens),
        )
        .where(UsoTokens.created_at >= datetime.now(timezone.utc) - timedelta(hours=horas))
        .group_by(UsoTokens.session_id)
        .order_by(func.min(UsoTokens.created_at).desc())
    ).all()

print(f"Sesiones en las ultimas {horas:g} h: {len(filas)}")
total = 0.0
for sid, inicio, llamadas, prompt, cache, salida in filas:
    g = {"prompt_tokens": prompt, "cached_tokens": cache, "output_tokens": salida}
    total += costo_usd(g)
    pct = 100.0 * cache / prompt if prompt else 0.0
    print(f"  {inicio:%Y-%m-%d %H:%M}  {sid[:16]:16}  {llamadas:3} llamadas  "
          f"{prompt:>8,} prompt  {pct:5.1f}% cache  {salida:>7,} salida  ->  ${costo_usd(g):.4f}")
print(f"TOTAL: ${total:.4f}")

# El almacenamiento del cache ($1/1M tok/hora, TTL 1h) NO cae en uso_tokens: se
# paga aparte y solo se ve en la factura de Google. Si pct_cache es 0 en todas
# las filas, caches.create esta fallando y no hay nada que amortizar.
if filas:
    pct_global = 100.0 * sum(f[4] for f in filas) / max(sum(f[3] for f in filas), 1)
    print(f"Cacheado global: {pct_global:.1f}%"
          + ("  <-- caches.create NO esta funcionando" if pct_global < 1 else ""))
    print("Ojo: falta el almacenamiento del cache, que esta tabla no registra.")
