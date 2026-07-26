"""
Augment the Athlete_10000_add.xlsx file with additional columns:
  - gender  (inferred from name patterns)
  - age     (random, realistic for youth athletes: 10-18)
  - district (random from Bihar districts, weighted by population)

Output: Athlete_10000_augmented.xlsx
"""

import random
import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

# ── 1. Load ────────────────────────────────────────────────────────────
df = pd.read_excel("Athlete_10000_add.xlsx")
print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

# ── 2. Gender inference ────────────────────────────────────────────────
FEMALE_MARKERS = [
    "kumari", "khatoon", "fatma", "begam", "begum", "devi", "naz",
    "priya", "kiran", "neha", "riya", "jyoti", "shreya", "sakshi",
    "anjali", "pooja", "nikita", "swati", "monika", "dipika", "deepika",
    "suman kumari", "guddi", "monu kumari", "gudiya", "kajal", "rani",
    "nisha", "khushi", "anita", "sunita", "geeta", "seema", "reena",
    "meena", "shanti", "lata", "savita", "kavita", "mamta", "rekha",
    "rubina", "shabnam", "shavnam", "nasreen", "nasiha", "hadiya",
    "muskan", "rukhsar", "gulshan", "afsana", "shabrin", "salma",
    "amina", "bibi", "parveen", "tabassum", "rizwana", "firdaus",
    "chanda", "chandani", "radha", "sarswati", "saraswati", "laxmi",
    "lakshmi", "sita", "draupadi", "prabha", "usha", "asha", "mala",
    "karishma", "manisha", "garima", "shikha", "rachna", "archana",
    "richa", "priyanka", "ankita", "pallavi", "sneha", "divya",
    "arti", "aarti", "bhawna", "chhaya", "renu", "bina", "mina",
    "tina", "pinki", "rinki", "babita", "kabita", "lalita", "vinita",
    "smriti", "kriti", "preeti", "nitu", "ritu", "mitu",
    "dipa", "monu devi", "soni", "baby", "dolly", "lucky kumari",
    "nilam", "punam", "sapna", "sweta", "shweta", "jhalki",
    "mona", "minu", "ranjana", "gunja", "nitam kumari",
    "milan kumari", "rakhi", "rishu kumari",
]

MALE_MARKERS = [
    "kumar", "raj", "singh", "khan", "alam", "ansari", "md ", "md.",
    "mohammad", "mohammed", "muhammed", "ram", "lal", "prasad",
    "gupt", "gupta", "ray", "yadav", "thakur", "mishra", "pandey",
    "sharma", "verma", "sah", "sahni", "paswan", "manjhi", "mahto",
    "prince", "rahul", "rohit", "mohit", "amit", "sumit", "ankit",
    "vikas", "vikash", "ravi", "suraj", "aditya", "arjun", "aryan",
    "karan", "gautam", "naveen", "praveen", "pradeep", "deepak",
    "rakesh", "mukesh", "suresh", "dinesh", "ganesh", "lokesh",
    "hariom", "shubham", "subham", "subhanshu", "niraj", "dhiraj",
    "aman", "sahil", "kishan", "mohan", "sohan", "rohan", "farhan",
    "rustam", "quadir", "qamar", "jisan", "mazid", "ghulam",
    "arbaz", "albats", "auranzeb", "noor mojassam", "arman",
    "ayush", "rishu raj", "amarjeet", "sajana praween",
    "tapeshwar", "noman",
]


def infer_gender(name: str) -> str:
    name_lower = str(name).strip().lower()

    # Check female markers first (kumari before kumar)
    for marker in FEMALE_MARKERS:
        if marker in name_lower:
            return "Female"

    for marker in MALE_MARKERS:
        if marker in name_lower:
            return "Male"

    # Fallback heuristic: names ending in 'a'/'i' lean female in Hindi
    if name_lower.endswith("a") or name_lower.endswith("i"):
        return "Female"

    return "Male"


df["gender"] = df["studentName"].apply(infer_gender)
print(f"Gender distribution:\n{df['gender'].value_counts()}")

# ── 3. Age (realistic youth athlete range) ─────────────────────────────
# Weighted toward 13-16 (most common youth sport testing age)
age_weights = {10: 0.04, 11: 0.06, 12: 0.10, 13: 0.15, 14: 0.20,
               15: 0.18, 16: 0.14, 17: 0.08, 18: 0.05}
ages = list(age_weights.keys())
probs = list(age_weights.values())
df["age"] = np.random.choice(ages, size=len(df), p=probs)
print(f"\nAge distribution:\n{df['age'].value_counts().sort_index()}")

# ── 4. District / Location (Bihar districts, weighted) ─────────────────
# Major Bihar districts with approximate relative population weights
BIHAR_DISTRICTS = {
    "Patna": 0.058,
    "East Champaran": 0.051,
    "West Champaran": 0.039,
    "Muzaffarpur": 0.048,
    "Darbhanga": 0.039,
    "Samastipur": 0.042,
    "Saran": 0.039,
    "Vaishali": 0.035,
    "Bhagalpur": 0.030,
    "Gaya": 0.044,
    "Begusarai": 0.030,
    "Purnia": 0.033,
    "Madhubani": 0.045,
    "Sitamarhi": 0.034,
    "Nalanda": 0.028,
    "Rohtas": 0.030,
    "Aurangabad": 0.025,
    "Katihar": 0.031,
    "Munger": 0.014,
    "Saharsa": 0.019,
    "Siwan": 0.033,
    "Gopalganj": 0.025,
    "Bhojpur": 0.027,
    "Buxar": 0.017,
    "Madhepura": 0.020,
    "Araria": 0.028,
    "Kishanganj": 0.016,
    "Supaul": 0.022,
    "Nawada": 0.022,
    "Jamui": 0.018,
    "Jehanabad": 0.011,
    "Arwal": 0.007,
    "Banka": 0.020,
    "Khagaria": 0.016,
    "Sheikhpura": 0.006,
    "Sheohar": 0.006,
    "Lakhisarai": 0.010,
    "Kaimur": 0.016,
}

districts = list(BIHAR_DISTRICTS.keys())
dist_probs = np.array(list(BIHAR_DISTRICTS.values()), dtype=float)
dist_probs /= dist_probs.sum()  # Normalise to ensure sum == 1.0
df["district"] = np.random.choice(districts, size=len(df), p=dist_probs)
print(f"\nDistrict distribution:\n{df['district'].value_counts()}")

# ── 5. Write output ────────────────────────────────────────────────────
output_file = "Athlete_10000_augmented.xlsx"
df.to_excel(output_file, index=False)
print(f"\n✅ Augmented file saved as '{output_file}' with {len(df)} rows and columns: {list(df.columns)}")
