#!/usr/bin/env python3
"""One-shot i18n drift fix for packages/landing/i18n.ts.

Replaces 8 stale strings + 3 stale comments per topics/bijou-pricing-drift-state.md.
After the fix, the file should be re-verified with `npx tsc --noEmit`.

This script is idempotent — running it twice is safe (second run finds 0 hits for each pattern).
"""
from pathlib import Path
import re
import sys

I18N = Path(__file__).resolve().parent.parent / "packages" / "landing" / "i18n.ts"

# (old, new, label) — old must be unique in the file. New mirrors the EN truth at L125.
REPLACEMENTS = [
    # === EN: features.kb.desc (long text) + features.kb.b1 ===
    (
        "Upload up to 50 FAQs and 2 documents.",
        "Upload up to 200 documents.",
        "EN L396 features.kb.desc",
    ),
    (
        "50 FAQs + 2 document uploads (Pro)",
        "200 documents (Pro)",
        "EN L397 features.kb.b1",
    ),

    # === MS: pricing.pro.features.9 + features.kb.desc + features.kb.b1 ===
    (
        "Pangkalan Pengetahuan \u2014 50 FAQ / 2 dokumen",
        "Pangkalan Pengetahuan \u2014 200 dokumen (termasuk FAQ)",
        "MS L641 pricing.pro.features.9",
    ),
    (
        "Muat naik sehingga 50 FAQ dan 2 dokumen.",
        "Muat naik sehingga 200 dokumen.",
        "MS L911 features.kb.desc",
    ),
    (
        "50 FAQ + 2 muat naik dokumen (Pro)",
        "200 dokumen (Pro)",
        "MS L912 features.kb.b1",
    ),

    # === ZH: pricing.pro.features.9 + features.kb.desc + features.kb.b1 ===
    (
        "\u77e5\u8bc6\u5e93 \u2014 50\u4e2aFAQ / \u6700\u591a2\u4efd\u6587\u4ef6",
        "\u77e5\u8bc6\u5e93 \u2014 200\u4efd\u6587\u4ef6 (\u5305\u542bFAQ)",
        "ZH L1149 pricing.pro.features.9",
    ),
    (
        "\u4e0a\u4f20\u6700\u591a50\u4e2aFAQ\u548c2\u4efd\u6587\u4ef6\u3002",
        "\u4e0a\u4f20\u6700\u591a200\u4efd\u6587\u4ef6\u3002",
        "ZH L1406 features.kb.desc",
    ),
    (
        "50\u4e2aFAQ + 2\u4efd\u6587\u4ef6\u4e0a\u4f20\uff08Pro\uff09",
        "200\u4efd\u6587\u4ef6\uff08Pro\uff09",
        "ZH L1407 features.kb.b1",
    ),

    # === TA: pricing.pro.features.9 + features.kb.desc + features.kb.b1 ===
    (
        "\u0b85\u0bb1\u0bbf\u0bb5\u0bc1\u0ba4\u0bcd \u0ba4\u0bb3\u0bae\u0bcd \u2014 50 FAQ / \u0bae\u0bc7\u0bb2\u0bcd 2 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bcd",
        "\u0b85\u0bb1\u0bbf\u0bb5\u0bc1\u0ba4\u0bcd \u0ba4\u0bb3\u0bae\u0bcd \u2014 200 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bcd (FAQ \u0b89\u0bb3\u0bcd\u0bb3\u0b9f\u0b99\u0bcd\u0b95\u0bc1\u0bae\u0bcd)",
        "TA L1655 pricing.pro.features.9",
    ),
    (
        "50 FAQ \u0bae\u0bb1\u0bcd\u0bb1\u0bc1\u0bae\u0bcd 2 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0baa\u0ba4\u0bbf\u0bb5\u0bc7\u0bb1\u0bcd\u0bb1\u0bb5\u0bc1\u0bae\u0bcd.",
        "200 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bc8 \u0baa\u0ba4\u0bbf\u0bb5\u0bc7\u0bb1\u0bcd\u0bb1\u0bb5\u0bc1\u0bae\u0bcd.",
        "TA L1935 features.kb.desc",
    ),
    (
        "50 FAQ + 2 \u0b86\u0bb5\u0ba3 \u0baa\u0ba4\u0bbf\u0bb5\u0bc7\u0bb1\u0bcd\u0bb1\u0b99\u0bcd\u0b95\u0bb3\u0bcd (Pro)",
        "200 \u0b86\u0bb5\u0ba3\u0b99\u0bcd\u0b95\u0bb3\u0bcd (Pro)",
        "TA L1936 features.kb.b1",
    ),

    # === Stale comments: RM 249/Mac 2026 -> RM 299/current month ===
    (
        "Pricing Section \u2014 Satu Peringkat PRO (RM 249/bulan, dikemaskini Mac 2026)",
        "Pricing Section \u2014 Satu Peringkat PRO (RM 299/bulan, dikemaskini Ogos 2026)",
        "MS L585 stale comment",
    ),
    (
        "\u5b9a\u4ef7\u90e8\u5206 \u2014 \u5355\u4e00PRO\u5957\u9910\uff08RM 249/\u6708\uff0c2026\u5e743\u6708\u66f4\u65b0\uff09",
        "\u5b9a\u4ef7\u90e8\u5206 \u2014 \u5355\u4e00PRO\u5957\u9910\uff08RM 299/\u6708\uff0c2026\u5e748\u6708\u66f4\u65b0\uff09",
        "ZH L1104 stale comment",
    ),
    (
        "\u0bb5\u0bbf\u0bb2\u0bc8 \u0baa\u0bbf\u0bb0\u0bbf\u0bb5\u0bc1 \u2014 \u0b92\u0bb1\u0bcd\u0bb1\u0bc8 PRO \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bcd (RM 249/\u0bae\u0bbe\u0ba4\u0bae\u0bcd, \u0bae\u0bbe\u0bb0\u0bcd\u0b9a\u0bcd 2026 \u0baa\u0bc1\u0ba4\u0bc1\u0baa\u0bcd\u0baa\u0bbf\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1)",
        "\u0bb5\u0bbf\u0bb2\u0bc8 \u0baa\u0bbf\u0bb0\u0bbf\u0bb5\u0bc1 \u2014 \u0b92\u0bb1\u0bcd\u0bb1\u0bc8 PRO \u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bcd (RM 299/\u0bae\u0bbe\u0ba4\u0bae\u0bcd, \u0b86\u0b95\u0bb8\u0bcd\u0b9f\u0bcd 2026 \u0baa\u0bc1\u0ba4\u0bc1\u0baa\u0bcd\u0baa\u0bbf\u0b95\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f\u0ba4\u0bc1)",
        "TA L1595 stale comment",
    ),
]


def main() -> int:
    if not I18N.exists():
        print(f"NOT FOUND: {I18N}", file=sys.stderr)
        return 2

    text = I18N.read_text(encoding="utf-8")
    hits = 0
    misses = []

    for old, new, label in REPLACEMENTS:
        count = text.count(old)
        if count == 1:
            text = text.replace(old, new)
            print(f"  . {label}: 1 hit, replaced")
            hits += 1
        elif count == 0:
            print(f"  ! {label}: 0 hits (NOT FOUND)")
            misses.append(label)
        else:
            print(f"  ! {label}: {count} hits (AMBIGUOUS — needs disambiguation)")
            misses.append(label)

    print()
    print(f"Summary: {hits} replaced, {len(misses)} missed")
    if misses:
        print("MISSED:", file=sys.stderr)
        for m in misses:
            print(f"  - {m}", file=sys.stderr)
        return 1

    I18N.write_text(text, encoding="utf-8")
    print(f"Wrote: {I18N}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
