"""Carga los conceptos iniciales desde un fichero local NO versionado.

El fichero ``seed_conceptos.json`` contiene datos reales del autónomo y está
excluido del repositorio (ver ``.gitignore``). Si no existe, no se carga nada.
Hay una plantilla con datos ficticios en ``seed_conceptos.example.json``.

Formato del JSON::

    {
      "1": {
        "ingresos": [["Concepto", 1000.0, 21.0], ["Exento", 500.0, null]],
        "gastos":   [["Concepto gasto", 100.0]]
      }
    }

El IVA se expresa como porcentaje (21.0 = 21 %); ``null`` equivale a "N/A".
"""

import json
from decimal import Decimal
from pathlib import Path

_SEED_FILE = Path(__file__).with_name("seed_conceptos.json")


def _to_decimal(value) -> Decimal:
    return Decimal(str(value))


def _load() -> dict[int, dict[str, list[tuple]]]:
    if not _SEED_FILE.exists():
        return {}
    try:
        raw = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    data: dict[int, dict[str, list[tuple]]] = {}
    for q, block in raw.items():
        ingresos = [
            (str(c), _to_decimal(imp), None if iva is None else _to_decimal(iva))
            for c, imp, iva in block.get("ingresos", [])
        ]
        gastos = [(str(c), _to_decimal(imp)) for c, imp in block.get("gastos", [])]
        data[int(q)] = {"ingresos": ingresos, "gastos": gastos}
    return data


SEED_CONCEPTOS: dict[int, dict[str, list[tuple]]] = _load()
