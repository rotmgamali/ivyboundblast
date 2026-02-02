import os

output_file = "OMNIBOT_PRODUCTION_EXPORT.md"
base_dir = os.getcwd()

# Production files only (per Action Plan structure)
files_to_export = [
    # Documentation
    ("README", "README.md", "markdown"),
    ("Architecture", "ARCHITECTURE_FINAL.md", "markdown"),
    ("Environment Template", ".env.example", "text"),
    
    # Core
    ("Configuration", "config.py", "python"),
    ("Requirements", "requirements.txt", "text"),
    ("Main Entry Point", "pipeline.py", "python"),
    ("Dockerfile", "Dockerfile", "dockerfile"),
    
    # Pipeline
    ("Pipeline Router", "pipeline/router.py", "python"),
    ("Campaign Orchestrator", "pipeline/campaign_orchestrator.py", "python"),
    
    # Senders
    ("Mailreef Client", "senders/mailreef_client.py", "python"),
    ("Inbox Rotator", "senders/inbox_rotator.py", "python"),
    
    # Generators
    ("Email Generator", "generators/email_generator.py", "python"),
    
    # Warming
    ("Smartlead Client", "warming/smartlead_client.py", "python"),
    ("Warming Orchestrator", "warming/warming_orchestrator.py", "python"),
    
    # Templates
    ("School Template 1", "templates/school/email_1.txt", "text"),
    ("School Template 2", "templates/school/email_2.txt", "text"),
    ("School Template 3", "templates/school/email_3.txt", "text"),
    ("Real Estate Template 1", "templates/real_estate/email_1.txt", "text"),
    ("Real Estate Template 2", "templates/real_estate/email_2.txt", "text"),
    ("Real Estate Template 3", "templates/real_estate/email_3.txt", "text"),
    ("PAC Template 1", "templates/pac/email_1.txt", "text"),
    ("PAC Template 2", "templates/pac/email_2.txt", "text"),
    ("PAC Template 3", "templates/pac/email_3.txt", "text"),
    
    # Enrichment
    ("Serper Enricher", "Jobs/researcher/serp_enricher.py", "python"),
]

with open(output_file, "w", encoding='utf-8') as outfile:
    outfile.write("# OMNIBOT COLD EMAIL PLATFORM - PRODUCTION EXPORT\n\n")
    outfile.write("This export contains the complete production-ready codebase.\n\n")
    outfile.write("---\n\n")
    
    for title, path, lang in files_to_export:
        full_path = os.path.join(base_dir, path)
        outfile.write(f"## {title}\n")
        outfile.write(f"**File:** `{path}`\n\n")
        
        if os.path.exists(full_path):
            outfile.write(f"```{lang}\n")
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                outfile.write(f.read())
            outfile.write("\n```\n\n")
            print(f"✓ Exported: {path}")
        else:
            outfile.write("> File not found\n\n")
            print(f"✗ Missing: {path}")
        
        outfile.write("---\n\n")

print(f"\nExport complete: {output_file}")
