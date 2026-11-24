"""Protein maths: target from body weight, and top-ups from foods you have."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import protein  # noqa: E402

# 68 kg: 1.6 g/kg = 109 g a day, about 27 g per meal over 4 meals
assert protein.target_g(68) == (109, 27)
# the user's case: shake 24 g, milk 8 g, eggs 6 g, tuna 25 g. 50 g short -> tuna first (biggest per serving)
ups = protein.top_ups(50, {"Protein shake": 24, "Milk": 8, "Eggs": 6, "Tuna, canned": 25})
assert ups[0] == ("Tuna, canned", 2, 50), ups
assert sum(g for *_, g in ups) >= 50
assert protein.top_ups(0, {"Eggs": 6}) == []
assert len(protein.top_ups(500, {"Eggs": 6, "Milk": 8, "Bread": 4, "Oats": 5})) == 3  # never more than 3 tips
assert all(n <= 3 for _, n, _ in protein.top_ups(500, {"Eggs": 6}))  # never more than 3 servings of one food
# 32 g short: tuna (25 g), then an egg for the last 7 g, not a whole 24 g shake
assert protein.top_ups(32, {"Protein shake": 24, "Eggs": 6, "Tuna, canned": 25}) == [("Tuna, canned", 1, 25), ("Eggs", 1, 6)]
print("all passed")
