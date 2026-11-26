# mcp-indonesia

**MCP server for Indonesian data.** Gives Claude (and any [Model Context Protocol](https://modelcontextprotocol.io) client) reliable, offline tools for the things every Indonesian app deals with: addresses, region codes, bank statements, NIK, phone numbers, and *terbilang*.

> LLMs guess at region codes, get *terbilang* wrong on large numbers, and cannot read a password-protected bank e-statement. These tools give exact, deterministic answers.

## Tools

| Tool | What it does |
|---|---|
| `normalisasi_alamat` | Free-text address → street, RT/RW, kelurahan, kecamatan, kota/kab, provinsi, kode pos + **Kemendagri code** |
| `cari_wilayah` | Typo-tolerant region search at any level, optionally inside a parent code |
| `baca_mutasi_bank` | Read a BCA / Mandiri / BRI / BNI / generic statement (PDF, CSV, XLSX) and check the running balance |
| `info_nik` | Validate NIK structure and decode region, birth date, gender, age (structure only, not a Dukcapil lookup) |
| `normalisasi_telepon` | `0812-…` / `+62…` → E.164, mobile operator or landline area, wa.me link |
| `terbilang` | `1250000` → "satu juta dua ratus lima puluh ribu rupiah" |
| `format_rupiah` | `1250000` → `Rp1.250.000` |

All tools are read-only and run **locally**; no data leaves your machine.

Built on two standalone libraries from the same family:
- [`alamat-id`](../alamat-id): Indonesian address parser
- [`mutasi-bank`](../mutasi-bank): Indonesian bank statement parser

## Install

```bash
pip install mcp-indonesia
alamat data download      # optional: full region data down to village level
```

### Claude Desktop / Claude Code

```json
{
  "mcpServers": {
    "indonesia": {
      "command": "mcp-indonesia"
    }
  }
}
```

Claude Code: `claude mcp add indonesia -- mcp-indonesia`

Streamable HTTP instead of stdio: `mcp-indonesia --http`.

## Example prompts

- *"Rapikan kolom alamat di pelanggan.csv dan tambahkan kode wilayahnya."*
- *"Baca e-statement BCA ini (password 01011990), kelompokkan pengeluaran per kategori."*
- *"Buatkan kuitansi Rp 4.750.000 lengkap dengan terbilangnya."*
- *"Nomor WA ini operator apa: 0857 1234 5678?"*

## Development

```bash
pip install -e ../alamat-id -e ../mutasi-bank -e ".[dev]"
pytest
```

## License

MIT
