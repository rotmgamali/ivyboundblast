def clean_name(n):
    n = n.split('-')[0].split('|')[0] 
    return n.strip()

test_names = [
    "Saint Vincent High School",
    "Lincoln Co. High School",
    "Incarnate Word Academy",
    "Riverstone School | Boise"
]

for name in test_names:
    print(f"Original: {name} -> Cleaned: '{clean_name(name)}'")
