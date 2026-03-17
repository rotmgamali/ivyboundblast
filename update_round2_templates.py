import os
from pathlib import Path

# Paths to archetype folders
TEMPLATE_ROOT = Path("/Users/mac/Ivybound/templates/school")
ARCHETYPES = [
    "principal", "head_of_school", "academic_dean", "college_counseling",
    "business_manager", "faith_leader", "athletics", "admissions", "general"
]

# The Round 2 Content
ROUND2_CONTENT = """Subject: Scholarship ROI for {{ school_name }} families

Following up on my previous note to {{ school_name }}. Most of the School Directors we partner with are currently focused on maximizing college financial aid opportunities for their families.

We’ve found that our $375 intensive test prep program is often the deciding factor in students qualifying for merit-based scholarships—averaging over $15,000 in aid per student. 

For your families, this represents a significant value-add that costs the school nothing to implement. Is this something you'd be open to discussing for 10 minutes? I'd love to share the case study from comparable schools.

Best regards,
Mark Greenstein
"""

def update_templates():
    for arch in ARCHETYPES:
        folder = TEMPLATE_ROOT / arch
        if not folder.exists():
            folder.mkdir(parents=True)
            
        target_file = folder / "email_1.txt"
        print(f"Updating {target_file}...")
        
        # Add a tiny bit of role-specific flavor if it's counseling or business
        content = ROUND2_CONTENT
        if arch == "college_counseling":
            content = content.replace("School Directors", "College Counselors")
        elif arch == "business_manager":
            content = content.replace("School Directors", "Business Managers")
        elif arch == "faith_leader":
            content = content.replace("School Directors", "Faith Leaders")
        elif arch == "athletics":
            content = content.replace("School Directors", "Athletic Directors")
            
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content.strip())

    print("Success: All Round 2 (Email 1) templates have been updated.")

if __name__ == "__main__":
    update_templates()
