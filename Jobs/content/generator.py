import openai
import os
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

SYSTEM_PROMPT = """You are Andrew, a Director of Educational Partnerships at Ivybound. 
You are writing a ONE-TO-ONE email to a school administrator (Superintendents, Principals, or Academic Deans).

**1. IDENTIFY SCHOOL NAME:**
*   Look for the official name of the school or institution in the provided Website Context.
*   If the website context is unclear or belongs to a different entity, use the provided Title as a backup.
*   Return the identified school name at the very top of your response, followed by "---NAME_END---".

**2. EMAIL BODY INSTRUCTIONS:**
*   **Vibe:** Professional, consultative, and respectful of their time. 
*   **Hyper-Personalization:** Use the **identified school name** naturally in the body. Build the hook by weaving in specific, unique details from their website (e.g., mention a specific program, mission statement quote, or recent accolade). Show you've actually visited their site.
*   **Structure:**
    *   **Salutation:** "Hi [Name]," or "Dear [Title] [Last Name],"
    *   **The Hook:** A deeply researched, 1-sentence hook about their school's specific programs or mission.
    *   **The Pivot:** "I'm reaching out because Ivybound helps schools expand their course offerings (AP, electives, etc.) without the overhead of hiring new full-time staff. We share high-quality courses between partner schools."
    *   **The Value:** "Our model generates $50k-$150k in annual revenue for the school while serving more students."
    *   **The Ask:** "Would you be open to a 10-minute briefing on how this partnership could benefit your students?"
*   **Format:** Plain text. Professional subject line related to the hook or partnership. 4-5 sentences MAX.
*   **CRITICAL:** Separate the Email and the SMS Script with exactly three pipe characters: `|||`.

**3. SMS SCRIPT INSTRUCTIONS (Use this EXACT Template):**
"Hi [Name], I'm Andrew from Ivybound. I sent you an email about our course-sharing partnership model that can help expand your curriculum while generating revenue. Would love to chat if you're interested? - Andrew"

Guidelines for SMS: 
* Keep it very brief and professional.
* Do NOT use the school name in the SMS.
"""

def generate_pitch(business_data):
    """
    Generates school name, email pitch AND sms follow-up.
    Returns tuple: (school_name, email_body, sms_script)
    """
    title = business_data.get("title", "Partner")
    website_text = business_data.get("website_content", "")
    email = business_data.get("email", "")
    has_email = "YES" if email and "@" in email else "NO"
    
    context = f"""
    Title from Maps: {title}
    Address: {business_data.get("address", "USA")}
    Phone: {business_data.get("phone", "Unknown")}
    Has Valid Email: {has_email}
    Website Context: {website_text[:5000]}
    """

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze and write high-quality pitch for:\n{context}"}
            ],
            temperature=0.4
        )
        content = response.choices[0].message.content
        
        # 1. Extract School Name
        school_name = title # Default
        if "---NAME_END---" in content:
            name_part, rest = content.split("---NAME_END---", 1)
            school_name = name_part.strip()
            content = rest.strip()
        
        # 2. Robust Parsing for Email/SMS
        if "|||" in content:
            email, sms = content.split("|||", 1)
            return school_name, email.strip(), sms.strip()
        
        if "SMS Script:" in content:
            parts = content.split("SMS Script:", 1)
            return school_name, parts[0].strip(), parts[1].strip()

        # Fallback SMS
        generic_sms = "Hi, I sent you a quick email about our course-sharing partnership model. Would love to chat if you're interested? - Andrew"
        return school_name, content.strip(), generic_sms
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        return title, "Hey, I was researching your school and wanted to connect about curriculum expansion.", "Hi, I sent you a quick email about our partnership model. - Andrew"

def enrich_leads_with_pitch(leads):
    print("🧠 Generating hyper-personalized pitches (100k Offer)...")
    enriched = []
    for lead in leads:
        pitch = generate_pitch(lead)
        lead['generated_pitch'] = pitch
        enriched.append(lead)
        print(f"   > Pitch generated for {lead.get('title')}")
    return enriched
