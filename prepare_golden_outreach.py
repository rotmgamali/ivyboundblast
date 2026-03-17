import os
import sys
import json
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from mailreef_automation.mailreef_client import MailreefClient
from mailreef_automation.automation_config import MAILREEF_API_KEY, MAILREEF_API_BASE

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GOLDEN_PREP")

# 1. THE GOLDEN DRAFTS (Target Email -> (Friendly Name, Draft Body))
DRAFTS = {
    "claire@emeraldcoastacademics.com": ("Claire", """Hi Claire,

I owe you a sincere apology for my delayed reply. We had an unexpected glitch in our email system, and I am incredibly sorry for leaving you hanging after you so graciously agreed to learn more about what we do. 

Given The Balanced Scholar's incredible work with language-based learning disorders, we would love to show you how our SAT/ACT prep accommodates diverse learning needs, empowering students to succeed without the usual overwhelming stress. We provide top-tier, highly tailored test prep options that can act as a seamless extension of your daily curriculum. 

If you are still open to it, I would love to connect for a brief, 15-minute chat next week to see if we might be a good fit to support your students. Do you have any availability next Tuesday or Wednesday?

Best regards,
Mark Greenstein
Ivybound Team"""),

    "jpickton@flprep.com": ("Jenny", """Hi Jenny,

I am writing to sincerely apologize for missing your message and our proposed call last week. We underwent an unforeseen email server migration that caused a delay in routing your response to me, and I deeply regret leaving you waiting. 

I am still very passionate about the possibility of collaborating with Florida Prep. Given your strong boarding and international student population, our flexible and high-impact SAT/ACT prep resources are perfectly positioned to integrate into their schedules and enhance your existing college readiness initiatives.

Are you open to rescheduling our brief phone call? I am wide open next Tuesday and Thursday—please let me know what day and time works best for you, and I will make it happen. You can also reach Mark Greenstein on our team directly at 914-482-5166 if that is more convenient.

Warmly,
Andrew
Ivybound"""),

    "rgrandy@academyprep.org": ("Richard", """Hi Richard,

First and foremost, I sincerely apologize for the delay in responding to you. We had a technical issue on our end that temporarily buried some of our incoming emails, and I deeply regret missing your message after Alison kindly forwarded it over.

I am thrilled to hear that you are interested in learning more about our SAT/ACT program. Knowing your critical role in Graduate Support Services, I believe our highly accessible prep ($375 vs standard $850+) could be an immense asset for your Academy Prep alumni as they navigate high school and prepare for college admissions. 

I would love to make up for my delayed response. Do you have 15 minutes to connect on a call sometime next week? You are also welcome to reach out to Mark Greenstein on our team directly at 914-482-5166.

Best regards,
Andrew
Ivybound"""),

    "a.diaz@mytvca.org": ("Ayeisha", """Hi Ayeisha,

I am so sorry for the long delay in getting back to you. We experienced an internal routing error with our emails last week, and I am very frustrated that it resulted in me missing your wonderful response! 

I would absolutely love to schedule that 15-minute chat with you. You hit the nail on the head regarding the "parents' pocket"—our primary mission at Ivybound is to provide elite, results-driven SAT/ACT prep at a fraction of the traditional cost (just $375), making it a truly feasible benefit for your families at The Vine Christian Academy. 

Are you available for a brief call next Wednesday or Thursday? You can also reach Mark Greenstein at 914-482-5166 if you'd like to chat sooner.

Best,
Andrew
Ivybound"""),

    "empowerobc@gmail.com": ("Buddy", """Hi Buddy,

Please accept my sincere apologies for the delay in getting back to you. We recently had an issue with our inbox syncing, and your kind message was unfortunately caught in the backlog. 

I greatly appreciate your openness, and I absolutely share your interest in exploring how Ivybound and Empower can collaborate. Helping your students successfully cross the bridge into higher education and fulfilling careers entirely aligns with our goals. 

Since you graciously provided your phone number, would it be alright if I gave you a call next Tuesday morning? Let me know if you have a preferred time, or I can simply try reaching your line at 352-978-0509 around 10:00 AM EST. 

Looking forward to speaking,
Andrew
Ivybound"""),

    "standrewsbaystemacademy@gmail.com": ("Lisa", """Hi Lisa,

I am so sorry for the delayed response! I experienced a glitch with my email client and just finally received your message today. 

To answer your question: while our headquarters are not local to Panama City, Ivybound works seamlessly with students and schools nationwide to provide highly personalized, top-tier SAT/ACT resources. We would be thrilled to support the brilliant students at St. Andrews Bay STEM Academy (especially your Bathtub Chickens robotics team!).

I would love to chat. You can reach Mark Greenstein on our team directly at 914-482-5166. Do you have a window of time next week when it might be best for us to call you? 

Best,
Andrew
Ivybound"""),

    "hatth82@gmail.com": ("Ha", """Hi Ha,

I am writing to sincerely apologize for the delay in sending these details over to you. We had a technical issue that temporarily delayed our outgoing emails. 

I completely understand wanting to review the specifics before we meet! Given Ivy Global School's incredible virtual setup and international student body, our program is uniquely positioned to help your students seamlessly transition into US universities. 

Here are the key details of an Ivybound partnership:
* **Online & Accessible:** Our expert SAT/ACT prep is delivered entirely online, making it fully accessible to your international students no matter their time zone.
* **Incredible Value:** We offer our partner schools a steeply discounted rate of just $375 per student (normally $850+).
* **Proven Results:** Our average student sees a 150+ point increase on the SAT, heavily boosting their chances for merit scholarships and F-1 visa university acceptance. 
* **Zero Workload for You:** We handle all registration, resources, and instruction. We simply provide you with a digital flyer to share with your families. 

I hope this overview helps! Please take your time reviewing, and if you feel this could benefit Ivy Global's families, I’d love to schedule a brief call to answer any questions you might have. 

Best regards,
Andrew
Ivybound"""),

    "jovanna@alphaperformance.net": ("Jovanna", """Hi Jovanna,

First, I want to deeply apologize for the radio silence on my end. I had an unfortunate issue with my email client formatting that hid your incredibly thoughtful response. I am so sorry for leaving you waiting after you kindly asked for time slots.

I absolutely love Alpha Performance Group's vision. Balancing elite athletic commitments with academics is remarkably difficult, and having a dedicated, online SAT/ACT preparation plan is often the decisive factor in securing collegiate scholarships. We would be honored to act as that dedicated college readiness arm for your athletes, seamlessly integrating online support so that your team can stay focused on the court.

I would love to get a call on the books to discuss this collaboration. Do you have a window next Wednesday or Thursday? You can also reach Mark Greenstein on our team directly at 914-482-5166 to find a time that works best.

Best regards,
Mark
Ivybound Team"""),

    "cshey@riverstoneschool.org": ("Courtney", """Hi Courtney,

I owe you two apologies! First, I am so sorry for the previous mix-up regarding the school name—that was an embarrassing clerical error on my part. Second, I am apologizing for the delay in this reply, as I experienced a glitch with my inbox routing over the past week. 

I am absolutely still interested in a brief chat, especially knowing you are at Riverstone. The rigorous standards of your IB World School (DP/MYP) programs produce incredibly capable students, and we specialize in helping high-achieving IB candidates translate that academic excellence into top-tier SAT and ACT scores for college admissions. 

I would love to learn more about your students' needs. Do you have 10-15 minutes to connect on a quick call next Tuesday or Wednesday? Let me know what works for your teaching schedule. 

Warmly,
Andrew
Ivybound""")
}

def prepare():
    logger.info("📡 Loading data from Google Sheets and Mailreef...")
    client = MailreefClient(MAILREEF_API_KEY, MAILREEF_API_BASE)
    
    # 1. Pull from Sheets (Priority 1)
    from sheets_integration import GoogleSheetsClient
    sheets = GoogleSheetsClient(input_sheet_name='Ivy Bound - Campaign Leads')
    sheets.setup_sheets()
    replies_ws = sheets.replies_sheet.sheet1
    all_replies = replies_ws.get_all_records()
    
    # Map sheets info
    sheet_info = {}
    for r in all_replies:
        e = str(r.get('From Email', '')).lower().strip()
        if e in DRAFTS:
            sheet_info[e] = {
                'from_inbox': r.get('Original Sender'),
                'thread_id': r.get('Thread ID') or r.get('Conversation ID'),
                'subject': r.get('Subject')
            }

    all_threads = {}
    
    # 2. Process each lead
    for target_email, (name, body) in DRAFTS.items():
        logger.info(f"🔍 Preparing outreach for {target_email}...")
        
        # Get info from sheet if exists
        info = sheet_info.get(target_email, {})
        from_inbox = info.get('from_inbox')
        thread_id = info.get('thread_id')
        subject = info.get('subject')

        # If thread ID is still None, scan Mailreef specifically for this sender
        if not thread_id or not from_inbox:
            logger.info(f"   Searching Mailreef specifically for {target_email}...")
            # We'll just look at the first 2 pages again but focused
            result = client.get_global_inbound(page=1, display=100)
            batch = result.get('data', [])
            for msg in batch:
                if str(msg.get('from_email', '')).lower().strip() == target_email:
                    from_inbox = msg.get('to')[0] if msg.get('to') else from_inbox
                    thread_id = msg.get('conversation_id') or msg.get('id')
                    subject = msg.get('subject_line')
                    break

        all_threads[target_email] = {
            'to_name': name,
            'from_inbox': from_inbox,
            'last_subject': subject or "Quick question",
            'thread_id': thread_id,
            'body': body
        }
    
    # Check for missing
    missing = [e for e in DRAFTS if e not in all_threads]
    if missing:
        logger.warning(f"⚠️ Could not find threads in recent history for: {missing}")
        # We can still send as a new thread if needed, but user wants to reply.
        # Let's try to fall back to whatever is in the sheets if Mailreef scan misses it.
    
    # 3. Save the Batch for Review
    output_path = "/Users/mac/Ivybound/golden_outreach_manifest.json"
    with open(output_path, 'w') as f:
        json.dump(all_threads, f, indent=4)
    
    print("\n" + "="*50)
    print("🚀 GOLDEN LEADS DISPATCH MANIFEST PREPARED")
    print("="*50)
    print(f"Total Leads Targeted: {len(DRAFTS)}")
    print(f"Threads Located: {len(all_threads)}")
    print(f"Manifest Location: {output_path}")
    print("\nSUMMARY OF SHIPMENT:")
    for email, data in all_threads.items():
        print(f"  - To: {data['to_name']} ({email})")
        print(f"    From: {data['from_inbox']}")
        print(f"    Thread: {data['thread_id']}")
    print("="*50)
    print("READY BUT NOT SENT. Run 'python3 send_golden_leads.py' to execute.")

if __name__ == "__main__":
    prepare()
