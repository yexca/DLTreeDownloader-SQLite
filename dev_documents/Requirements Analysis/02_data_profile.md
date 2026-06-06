# Data Profile

## 1. Workbook Shape

Observed workbook: `files/DL tree 260308.xlsx`

| Property | Value |
|---|---:|
| Sheets | 1 |
| Main sheet | `Sheet1` |
| Header row | Row 1 |
| Data rows | 74,917 |
| Columns | 11 |
| Duplicate work codes | 0 in current workbook |

## 2. Columns

| Position | Header | Observed data type | Required handling |
|---:|---|---|---|
| 1 | `RJcode` | Text code | Store as `work_code`, unique among visible works. |
| 2 | `标签` | Text / blank | Store raw text; optionally normalize tags later. |
| 3 | `MEGA链接` | JSON text | Parse into download link rows. |
| 4 | `销售日期` | Excel datetime / blank | Store as ISO date or null. |
| 5 | `声优` | Text / blank | Store raw text and normalized voice actor mapping. |
| 6 | `标题` | Text / blank | Store raw text. |
| 7 | `备注` | Text / `null` / blank | Normalize literal `null` to SQL null. |
| 8 | `类型` | Text / blank | Store raw text. |
| 9 | `社团` | Text / blank | Store raw text and normalized circle mapping. |
| 10 | `档案大小` | Human-readable size | Store raw text and optionally parsed bytes. |
| 11 | `MP3大小` | Human-readable size | Store raw text and optionally parsed bytes. |

## 3. Blank Counts

Blank or literal `null` counts observed:

| Column | Blank count |
|---|---:|
| `备注` | 65,109 |
| `标签` | 61,485 |
| `声优` | 19,703 |
| `销售日期` | 386 |
| `类型` | 113 |
| `社团` | 104 |
| `标题` | 99 |

Implication:

- The importer must accept missing metadata.
- Search result rendering must handle null title, voice actor, circle, and sale date gracefully.

## 4. Work Code Patterns

Observed code pattern counts:

| Pattern | Count | Example |
|---|---:|---|
| `RJ` followed by digits | 73,274 | `RJ01573968` |
| `d_` followed by digits | 725 | `d_724629` |
| `VJ` followed by digits | 610 | `VJ01005847` |
| Other | 308 | `BJ02370869` |

Implication:

- The CLI prompt can still say "RJcode" for user familiarity.
- Database and code should use `work_code`.
- Validation should reject empty codes but should not require `RJ\d+`.

## 5. MEGA Link JSON

All rows in the inspected workbook had parseable JSON in `MEGA链接`.

Observed shape:

```json
{
  "C": [
    {
      "F": "RJ01548502.zip",
      "L": "https://mega.nz/file/...",
      "S": "3249155727"
    },
    {
      "F": "RJ01548502.zip.par2",
      "L": "https://mega.nz/file/...",
      "S": "228886068"
    }
  ]
}
```

Observed keys:

- Root key: `C` in all rows.
- Link item fields:
  - `F`: file name
  - `L`: MEGA URL
  - `S`: byte size as string

Observed link count distribution highlights:

| Active files per work | Row count |
|---:|---:|
| 1 | 20,289 |
| 2 | 25,059 |
| 3 | 6,230 |
| 4 | 11,040 |
| 5 | 1,845 |
| 6 | 4,023 |
| 8 | 1,885 |
| 10 | 953 |

Implication:

- Download command must handle multiple links per work.
- Importer should store the JSON root category, currently `C`, to stay future-compatible.
- Disk checks should sum selected active link sizes.

## 6. Size Fields

Observed `档案大小` units:

- `MB`: 43,656
- `GB`: 30,630
- `B`: 514
- `KB`: 117

Observed `MP3大小` units:

- `B`: 48,324
- `MB`: 25,296
- `GB`: 1,292
- `KB`: 5

Implication:

- Human-readable sizes are useful for display.
- Exact download sizing should use link field `S`.
- Parsed bytes can still be stored for display sorting.

## 7. Voice Actor Field

Multiple voice actors are commonly separated by four spaces:

Examples:

```text
神代そら    海音ミヅチ
分倍河原シホ    西瓜すいか    麦咲輪紫葵
涼花みなせ    陽向葵ゅか    かの仔
```

Observed delimiter hints:

- Four spaces: 8,708 rows
- Japanese comma-like delimiter `、`: 69 rows
- Comma variants: 69 rows

Recommended v1 parsing:

1. Split on runs of two or more spaces.
2. Also split on `、`, `，`, and `,` only when there is no obvious reason to preserve the punctuation.
3. Trim all names.
4. Drop empty names.
5. Store the original raw value in `works.voice_actor_raw`.

## 8. Circle Field

Circle field is usually a single value, but may contain punctuation that is part of the official name:

Examples:

```text
K&Gの同人
&MORE
N&R
リリムワークス /【兎月りりむ。公式】（メスガキ?ロリ声優）
```

Recommended v1 parsing:

- Treat the whole `社团` cell as one circle name.
- Do not split on `/`, `&`, or punctuation for circles in v1.

## 9. Data Quality Rules

The importer should:

- Trim whitespace around all text fields.
- Convert empty strings and literal `null` to SQL null for optional fields.
- Preserve original text for tags, voice actors, notes, type, circle, and sizes.
- Fail the import if required columns are missing.
- Continue row-level import when optional fields are malformed.
- Report malformed MEGA JSON rows and skip their link rows.

