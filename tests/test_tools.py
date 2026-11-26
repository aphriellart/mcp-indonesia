import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from mcp_indonesia import tools
from mcp_indonesia.server import server


@pytest.mark.parametrize("n,expected", [
    (0, "nol"),
    (11, "sebelas"),
    (15, "lima belas"),
    (100, "seratus"),
    (115, "seratus lima belas"),
    (1000, "seribu"),
    (1001, "seribu satu"),
    (2500, "dua ribu lima ratus"),
    (1_250_000, "satu juta dua ratus lima puluh ribu"),
    (1_000_000_000, "satu miliar"),
    (101_000, "seratus satu ribu"),
    (-7, "minus tujuh"),
])
def test_terbilang(n, expected):
    assert tools.terbilang(n) == expected


def test_terbilang_rupiah():
    assert tools.terbilang(1_250_000, "rupiah") == "satu juta dua ratus lima puluh ribu rupiah"
    assert tools.terbilang("10.50", "rupiah") == "sepuluh rupiah lima puluh sen"
    assert tools.terbilang("3.14") == "tiga koma satu empat"
    assert tools.terbilang(2000, "rupiah", True) == "Dua Ribu Rupiah"


@pytest.mark.parametrize("raw,e164,op", [
    ("0812-3456-7890", "+6281234567890", "Telkomsel"),
    ("+62 857 1234 5678", "+6285712345678", "Indosat Ooredoo"),
    ("6287812345678", "+6287812345678", "XL Axiata"),
    ("(021) 5551234", "+62215551234", ""),
])
def test_phone(raw, e164, op):
    r = tools.normalisasi_telepon(raw)
    assert r["valid"] and r["e164"] == e164
    if op:
        assert r["operator"] == op
    else:
        assert r["jenis"] == "telepon tetap" and r["wilayah"].startswith("Jakarta")


def test_phone_invalid():
    assert not tools.normalisasi_telepon("0812")["valid"]


def test_nik():
    import alamat.gazetteer
    gz = alamat.gazetteer.default()
    # Synthetic NIK: Jawa Barat (32), regency 73, district 01, woman born 12-05-1995
    r = tools.info_nik("3273015205950001", gz, today=date(2026, 11, 27))
    assert r["valid"]
    assert r["jenis_kelamin"] == "perempuan"
    assert r["tanggal_lahir"] == "1995-05-12"
    assert r["umur"] == 31
    assert r["wilayah"]["provinsi"] == "Jawa Barat"
    r = tools.info_nik("3273011205100001", gz, today=date(2026, 11, 27))
    assert r["tanggal_lahir"] == "2010-05-12" and r["jenis_kelamin"] == "laki-laki"


@pytest.mark.parametrize("nik", ["123", "3273013205950001", "9973011205950001", "3273011205950000"])
def test_nik_invalid(nik):
    import alamat.gazetteer
    assert not tools.info_nik(nik, alamat.gazetteer.default())["valid"]


def test_rupiah():
    assert tools.format_rupiah(1250000) == "Rp1.250.000"
    assert tools.format_rupiah("-1500.5", True) == "-Rp1.500,50"


def test_server_lists_and_calls_tools(tmp_path):
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {"normalisasi_alamat", "cari_wilayah", "baca_mutasi_bank", "info_nik",
            "normalisasi_telepon", "terbilang", "format_rupiah"} <= names

    csv = tmp_path / "m.csv"
    csv.write_text("Tgl;Uraian;Debet;Kredit;Saldo\n"
                   "01/04/2026;SETORAN;;1.000.000,00;1.000.000,00\n"
                   "02/04/2026;QRIS;45.500,00;;954.500,00\n", encoding="utf-8")

    async def call(name, args):
        res = await server.call_tool(name, args)
        return res

    res = asyncio.run(call("baca_mutasi_bank", {"path": str(csv)}))
    text = json.dumps(res, default=str)
    assert "954500" in text
    res = asyncio.run(call("terbilang", {"angka": "2500"}))
    assert "dua ribu lima ratus rupiah" in json.dumps(res, default=str)
    res = asyncio.run(call("normalisasi_alamat", {"alamat": "jl. malioboro 52, jogja"}))
    assert "Daerah Istimewa Yogyakarta" in json.dumps(res, default=str)
