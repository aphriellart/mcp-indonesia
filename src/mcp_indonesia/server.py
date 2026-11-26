"""MCP server exposing Indonesian data tools to Claude and other MCP clients."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from . import __version__, tools

READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)

server = MCPServer(
    name="indonesia",
    title="Indonesia Data Tools",
    version=__version__,
    instructions=(
        "Tools for Indonesian data: normalise addresses and match them to official "
        "Kemendagri region codes, search regions, read bank statements (BCA, Mandiri, "
        "BRI, BNI, generic CSV/PDF), decode NIK structure, normalise phone numbers, "
        "and spell out numbers in Indonesian (terbilang). Everything runs locally."),
)


def _gz():
    import alamat.gazetteer

    return alamat.gazetteer.default()


@server.tool(annotations=READ_ONLY)
def normalisasi_alamat(alamat: str) -> dict:
    """Parse an Indonesian address and match it to official region codes.

    Returns street, number, RT/RW, kelurahan, kecamatan, kota/kabupaten,
    provinsi, postal code, the Kemendagri code, a confidence score and
    alternatives when the address is ambiguous.
    """
    import alamat as alamat_lib

    m = alamat_lib.normalize(alamat, _gz())
    d = m.to_dict()
    if not _gz().is_full:
        d["catatan"] = "Only province data is installed; run `alamat data download` for village-level matching."
    return d


@server.tool(annotations=READ_ONLY)
def cari_wilayah(nama: str,
                 tingkat: Literal["provinsi", "kota", "kecamatan", "kelurahan"] = "kota",
                 dalam_kode: str = "") -> list[dict]:
    """Search Indonesian regions by name (typo tolerant).

    `tingkat` is the level to search; `dalam_kode` limits the search to the
    descendants of a region code, e.g. "32" for Jawa Barat.
    """
    from alamat.gazetteer import FIELD_LEVEL

    gz = _gz()
    out = []
    for r, score in gz.find(FIELD_LEVEL[tingkat], nama, dalam_kode, limit=10, cutoff=0.7):
        out.append({"kode": r.code, "nama": r.name, "skor": round(score, 3),
                    "induk": gz._path_name(r.parent) if r.parent else ""})
    return out


@server.tool(annotations=READ_ONLY)
def baca_mutasi_bank(path: str, bank: str = "", password: str = "",
                     maks_transaksi: int = 500) -> dict:
    """Read an Indonesian bank statement file (PDF, CSV, XLSX, TXT) from disk.

    Returns the account, opening/closing balance, totals, a running-balance
    check and the transactions (positive amount = money in, negative = out).
    `bank` forces a parser (bca, bca-csv, mandiri, bri, bni, generic, generic-csv).
    """
    import mutasi

    p = Path(path).expanduser()
    if not p.is_file():
        raise ValueError(f"file not found: {p}")
    st = mutasi.parse(p, bank=bank or None, password=password or None)
    d = st.to_dict()
    d["masalah_saldo"] = st.validate()
    d["jumlah_transaksi"] = len(st.transactions)
    if len(d["transactions"]) > maks_transaksi:
        d["transactions"] = d["transactions"][:maks_transaksi]
        d["terpotong"] = True
    return d


@server.tool(annotations=READ_ONLY)
def info_nik(nik: str) -> dict:
    """Check the structure of an Indonesian NIK (KTP number) and decode it:
    region, birth date, gender, age. Structure only - not a Dukcapil lookup."""
    return tools.info_nik(nik, _gz())


@server.tool(annotations=READ_ONLY)
def normalisasi_telepon(nomor: str) -> dict:
    """Normalise an Indonesian phone number to +62 / 08 form and detect the
    mobile operator or landline area."""
    return tools.normalisasi_telepon(nomor)


@server.tool(annotations=READ_ONLY)
def terbilang(angka: str, mata_uang: str = "rupiah", huruf_besar: bool = False) -> str:
    """Spell out a number in Indonesian words (for invoices, receipts, cheques).
    Example: 1250000 -> 'satu juta dua ratus lima puluh ribu rupiah'."""
    return tools.terbilang(angka, mata_uang, huruf_besar)


@server.tool(annotations=READ_ONLY)
def format_rupiah(nilai: str, desimal: bool = False) -> str:
    """Format a number as Rupiah, e.g. 1250000 -> 'Rp1.250.000'."""
    return tools.format_rupiah(nilai, desimal)


def main() -> None:
    transport = "stdio"
    if "--http" in sys.argv:
        transport = "streamable-http"
    server.run(transport)


if __name__ == "__main__":  # pragma: no cover
    main()
