"""Unit test for the formula reference rewriting used when a bidder is added."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
import blocks  # noqa: E402

CASES = [
    # a single cross-sheet reference
    ("=Resume!B4", lambda s, r: r + 16 if s == "Resume" else r, "=Resume!B20"),
    # quoted sheet name, a range, and text in double quotes that looks like a cell (must stay)
    ("=IF(COUNTIF('Form 11a_Lot 1'!P11:P17,\"Qualified\")=7,\"Meet in L13\",\"Not Meet\")", lambda s, r: r + 512,
     "=IF(COUNTIF('Form 11a_Lot 1'!P523:P529,\"Qualified\")=7,\"Meet in L13\",\"Not Meet\")"),
    # absolute markers kept, a function name ending in digits untouched, whole-column reference untouched
    ("=SUM($C$5:C9)+LOG10(A2)+Sheet2!$A1+A:A", lambda s, r: r + 100, "=SUM($C$105:C109)+LOG10(A102)+Sheet2!$A101+A:A"),
    # only the bidder's own row moves
    ("=IF(AND(C4=\"Meet\",D4=\"Meet\"),\"Meet\",\"Not Meet\")", lambda s, r: 20 if s is None and r == 4 else r,
     "=IF(AND(C20=\"Meet\",D20=\"Meet\"),\"Meet\",\"Not Meet\")"),
    # a broken reference is left as it is
    ("=IF(AND(Administrasi!L13=\"Qualified\",#REF!=\"Qualified\"),1,0)", lambda s, r: r + 650,
     "=IF(AND(Administrasi!L663=\"Qualified\",#REF!=\"Qualified\"),1,0)"),
]

for formula, fn, want in CASES:
    got = blocks.map_rows(formula, fn)
    print("OK " if got == want else "BAD", got)
    assert got == want, want
print("all formula-rewrite cases pass")
