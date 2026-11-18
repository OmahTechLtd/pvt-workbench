"""Checks for the fluid classification and plus fraction modules. Run from the project folder with: python check_classification_fraction.py

Each check states what the published example prints and what this code returns."""
from classification import classify, reservoir_state, reservoir_kind
from plus_fraction import RIAZI_DAUBERT, edmister_omega, riazi_daubert, verification

failures = []


def check(label, ok):
    print(("ok    " if ok else "FAIL  ") + label)
    if not ok:
        failures.append(label)


# Example 1-1, p. 26
m, g = 150, 0.78
tb = riazi_daubert("tb", m, g)
pc = riazi_daubert("pc", m, g)
check("Tb = 825.26 degR", abs(tb - 825.26) <= 0.01)
check("pc = 320.3 psia", abs(pc - 320.3) <= 0.1)
tc_book = riazi_daubert("tc", m, g, {**RIAZI_DAUBERT["tc"], "a": 544.2})
check("Tc = 1139.4 degR when the worked line's constant 544.2 is used", abs(tc_book - 1139.4) <= 0.1)
check("Acentric factor = 0.5067 from the published printed Tc, pc and Tb", abs(edmister_omega(320.3, 1139.4, 825.26) - 0.5067) <= 0.0001)

# Known differences, recorded so a future change to the code does not hide them
vc = riazi_daubert("vc", m, g)
check("Vc differs from the printed 0.06035 (expected, see README)", abs(vc - 0.06035) > 0.001)
check("Tc with Table 1-4 constant 544.4 differs from the printed 1139.4 (expected)", abs(riazi_daubert("tc", m, g) - 1139.4) > 0.1)

rows = verification()["rows"]
check("verification table has 7 rows", len(rows) == 7)

# Classification limits, pp. 4 to 8
check("GOR 500, API 32 is ordinary black oil", classify(gor=500, api=32)["matches"] == ["ordinary_black"])
check("Bo 1.1, GOR 150, API 30 is low-shrinkage oil", classify(gor=150, bo=1.1, api=30)["matches"] == ["low_shrinkage"])
check("Bo 1.8, GOR 2500, API 50 is volatile oil", classify(gor=2500, bo=1.8, api=50)["matches"] == ["volatile"])
check("Bo 2.3, GOR 3500, C7+ 15 mol% is near-critical oil", classify(gor=3500, bo=2.3, c7plus=15)["matches"] == ["near_critical"])
check("GOR 1200 falls in the gap and matches no class", classify(gor=1200, bo=1.6, api=42)["matches"] == [])
check("Range ends are included (GOR 200 and 700)", classify(gor=200, api=15)["matches"] == ["ordinary_black"] and classify(gor=700, api=40)["matches"] == ["ordinary_black"])
check("GOR 3100, Bo 1.9 is volatile, Bo 2.1 is near-critical",
      classify(gor=3100, bo=1.9, api=50)["matches"] == ["volatile"] and classify(gor=3100, bo=2.1)["matches"] == ["near_critical"])

# Reservoir type, p. 3
check("pi above pb is undersaturated", reservoir_state(4000, 3000)["key"] == "undersaturated")
check("pi equal to pb is saturated", reservoir_state(3000, 3000)["key"] == "saturated")
check("pi below pb is gas-cap", reservoir_state(2000, 3000)["key"] == "gas_cap")
check("T below Tc is an oil reservoir", reservoir_kind(200, 400)["key"] == "oil")
check("T above Tc is a gas reservoir", reservoir_kind(300, 200)["key"] == "gas")

print()
print("All checks passed." if not failures else f"{len(failures)} check(s) failed.")
raise SystemExit(1 if failures else 0)
