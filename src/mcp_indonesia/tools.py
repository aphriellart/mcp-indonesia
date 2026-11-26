"""Pure functions behind the MCP tools (testable without an MCP client)."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation

# --------------------------------------------------------------------------- #
# Terbilang
# --------------------------------------------------------------------------- #
_SATUAN = ["", "satu", "dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan",
           "sembilan", "sepuluh", "sebelas"]
_SKALA = [(10**15, "kuadriliun"), (10**12, "triliun"), (10**9, "miliar"),
          (10**6, "juta"), (10**3, "ribu")]


def _ratusan(n: int) -> str:
    if n < 12:
        return _SATUAN[n]
    if n < 20:
        return f"{_SATUAN[n - 10]} belas"
    if n < 100:
        return f"{_SATUAN[n // 10]} puluh {_ratusan(n % 10)}".strip()
    if n < 200:
        return f"seratus {_ratusan(n - 100)}".strip()
    return f"{_SATUAN[n // 100]} ratus {_ratusan(n % 100)}".strip()


def _bulat(n: int) -> str:
    if n == 0:
        return "nol"
    parts = []
    for size, name in _SKALA:
        if n >= size:
            q, n = divmod(n, size)
            if size == 1000 and q == 1:
                parts.append("seribu")
            else:
                parts.append(f"{_bulat(q)} {name}")
    if n:
        parts.append(_ratusan(n))
    return " ".join(parts)


def terbilang(angka: str | int | float, mata_uang: str = "", huruf_besar: bool = False) -> str:
    """Convert a number to Indonesian words, e.g. for invoices and receipts.

    >>> terbilang(1_250_000, "rupiah")
    'satu juta dua ratus lima puluh ribu rupiah'
    """
    try:
        d = Decimal(str(angka).replace("_", "").strip())
    except InvalidOperation as exc:
        raise ValueError(f"bukan angka: {angka!r}") from exc
    if abs(d) >= Decimal(10) ** 18:
        raise ValueError("angka terlalu besar (maksimal di bawah 1 triliun triliun)")
    neg = d < 0
    d = abs(d)
    whole = int(d)
    text = _bulat(whole)
    frac = format(d, "f").split(".")[1].rstrip("0") if "." in format(d, "f") else ""
    if frac:
        if mata_uang.lower() == "rupiah":
            sen = int((frac + "0")[:2])
            if sen:   # "sepuluh rupiah lima puluh sen"
                text += f" {mata_uang} {_bulat(sen)} sen"
                mata_uang = ""
        else:
            text += " koma " + " ".join(_SATUAN[int(c)] if c != "0" else "nol" for c in frac)
    if mata_uang:
        text += f" {mata_uang}"
    if neg:
        text = "minus " + text
    text = re.sub(r"\s+", " ", text).strip()
    return text.title() if huruf_besar else text


# --------------------------------------------------------------------------- #
# Phone numbers
# --------------------------------------------------------------------------- #
OPERATOR = {
    "Telkomsel": ["811", "812", "813", "821", "822", "823", "851", "852", "853"],
    "Indosat Ooredoo": ["814", "815", "816", "855", "856", "857", "858"],
    "XL Axiata": ["817", "818", "819", "859", "877", "878"],
    "Axis": ["831", "832", "833", "838"],
    "Tri (3)": ["895", "896", "897", "898", "899"],
    "Smartfren": ["881", "882", "883", "884", "885", "886", "887", "888", "889"],
}
_PREFIX_OP = {p: op for op, ps in OPERATOR.items() for p in ps}
AREA = {
    "21": "Jakarta & sekitarnya", "22": "Bandung", "24": "Semarang", "31": "Surabaya",
    "61": "Medan", "274": "Yogyakarta", "361": "Denpasar", "411": "Makassar",
    "251": "Bogor", "341": "Malang", "711": "Palembang", "778": "Batam",
}


def normalisasi_telepon(nomor: str) -> dict:
    """Normalise an Indonesian phone number to +62 form and identify its type."""
    raw = nomor
    s = re.sub(r"[^\d+]", "", nomor or "")
    if s.startswith("+"):
        s = s[1:]
    if s.startswith("0062"):
        s = s[4:]
    elif s.startswith("62"):
        s = s[2:]
    elif s.startswith("0"):
        s = s[1:]
    out = {"input": raw, "valid": False, "e164": "", "lokal": "", "jenis": "", "operator": ""}
    if not s.isdigit():
        out["alasan"] = "bukan nomor telepon"
        return out
    if s.startswith("8"):
        out["jenis"] = "seluler"
        out["operator"] = _PREFIX_OP.get(s[:3], "tidak diketahui")
        ok = 9 <= len(s) <= 12
    else:
        out["jenis"] = "telepon tetap"
        area = next((a for a in sorted(AREA, key=len, reverse=True) if s.startswith(a)), "")
        out["wilayah"] = AREA.get(area, "")
        ok = 8 <= len(s) <= 11
    if not ok:
        out["alasan"] = "panjang nomor tidak wajar"
        return out
    out.update(valid=True, e164=f"+62{s}", lokal=f"0{s}",
               whatsapp=f"https://wa.me/62{s}" if s.startswith("8") else "")
    return out


# --------------------------------------------------------------------------- #
# NIK (Nomor Induk Kependudukan)
# --------------------------------------------------------------------------- #
def info_nik(nik: str, gazetteer=None, today: date | None = None) -> dict:
    """Validate the structure of a NIK and decode what it encodes.

    Layout: PP KK CC DDMMYY SSSS - province, regency, district, birth date
    (day + 40 for women), serial number. This checks structure only; it does
    not prove the NIK is registered at Dukcapil.
    """
    today = today or date.today()
    s = re.sub(r"\D", "", nik or "")
    out: dict = {"nik": s, "valid": False, "catatan": "Hanya validasi struktur, bukan verifikasi ke Dukcapil."}
    if len(s) != 16:
        out["alasan"] = f"NIK harus 16 digit (didapat {len(s)})"
        return out
    prov, kab, kec = s[0:2], s[2:4], s[4:6]
    dd, mm, yy, serial = int(s[6:8]), int(s[8:10]), int(s[10:12]), s[12:16]
    gender = "perempuan" if dd > 40 else "laki-laki"
    if dd > 40:
        dd -= 40
    year = 2000 + yy if 2000 + yy <= today.year else 1900 + yy
    try:
        born = date(year, mm, dd)
    except ValueError:
        out["alasan"] = "bagian tanggal lahir tidak valid"
        return out
    if serial == "0000":
        out["alasan"] = "nomor urut 0000 tidak valid"
        return out
    code = f"{prov}.{kab}.{kec}"
    region = {"kode_kecamatan": code}
    if gazetteer is not None:
        p = gazetteer.by_code.get(prov)
        if p is None:
            out["alasan"] = f"kode provinsi {prov} tidak dikenal"
            return out
        region["provinsi"] = p.display
        k = gazetteer.by_code.get(f"{prov}.{kab}")
        c = gazetteer.by_code.get(code)
        if k:
            region["kota"] = ("Kota " if k.jenis == "kota" else "Kab. ") + k.display
        if c:
            region["kecamatan"] = c.display
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    out.update(valid=True, wilayah=region, tanggal_lahir=born.isoformat(),
               jenis_kelamin=gender, umur=age, nomor_urut=serial)
    return out


# --------------------------------------------------------------------------- #
# Rupiah
# --------------------------------------------------------------------------- #
def format_rupiah(nilai: str | int | float, desimal: bool = False) -> str:
    d = Decimal(str(nilai))
    q = f"{abs(d):,.2f}" if desimal else f"{abs(d):,.0f}"
    q = q.replace(",", "_").replace(".", ",").replace("_", ".")
    return f"{'-' if d < 0 else ''}Rp{q}"
