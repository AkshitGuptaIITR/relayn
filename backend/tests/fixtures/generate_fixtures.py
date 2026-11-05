import datetime
import json
from pathlib import Path

# Base time for synthetic emails
NOW = datetime.datetime.now(datetime.timezone.utc)

def days_ago(d: int, hours: int = 0) -> str:
    dt = NOW - datetime.timedelta(days=d, hours=hours)
    return dt.isoformat()

SYNTHETIC_EMAILS = [
    # -------------------------------------------------------------
    # 1. STRIPE: Full lifecycle (Application -> Recruiter -> Assessment -> Offer)
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_stripe_01",
        "gmail_thread_id": "thread_stripe_01",
        "history_id": "1001",
        "sender": "jobs@stripe.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Thank you for applying to Stripe - Staff Backend Engineer",
        "sent_at": days_ago(30),
        "snippet": "Thanks for your interest in Stripe! We received your application for Staff Backend Engineer...",
        "body_plain": "Hi Akshit,\n\nThank you for applying for the Staff Backend Engineer role at Stripe. We have received your application and our team is currently reviewing your profile.\n\nYou can view the status of your application on our career portal.\n\nBest regards,\nThe Stripe Recruiting Team"
    },
    {
        "gmail_message_id": "msg_stripe_02",
        "gmail_thread_id": "thread_stripe_01",
        "history_id": "1002",
        "sender": "sarah.connor@stripe.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Stripe: Staff Backend Engineer - Let's connect!",
        "sent_at": days_ago(25),
        "snippet": "Hi Akshit, I'm Sarah from the technical recruiting team at Stripe. Your profile caught our eye...",
        "body_plain": "Hi Akshit,\n\nI lead backend hiring at Stripe. We were very impressed with your background in distributed systems and would love to chat for 30 minutes to discuss the Staff Backend Engineer position.\n\nCould you let me know if you are free this Thursday at 2:00 PM EST or Friday at 11:00 AM EST?\n\nLooking forward to speaking!\n\nSarah Connor\nTechnical Recruiter | Stripe"
    },
    {
        "gmail_message_id": "msg_stripe_03",
        "gmail_thread_id": "thread_stripe_01",
        "history_id": "1003",
        "sender": "sarah.connor@stripe.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Stripe Next Steps: Technical Assessment Invitation",
        "sent_at": days_ago(18),
        "snippet": "Great chatting with you! As discussed, the next step is our hands-on systems assessment...",
        "body_plain": "Hi Akshit,\n\nIt was great speaking with you earlier! The team wants to move forward to the technical assessment phase. Here is the link to complete our 90-minute systems design evaluation:\n\nhttps://assessment.stripe.com/take/xyz890\n\nPlease complete this assessment by next Tuesday, 5:00 PM EST.\n\nBest of luck!\nSarah Connor"
    },
    {
        "gmail_message_id": "msg_stripe_04",
        "gmail_thread_id": "thread_stripe_01",
        "history_id": "1004",
        "sender": "sarah.connor@stripe.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Congratulations! Offer from Stripe",
        "sent_at": days_ago(5),
        "snippet": "We are thrilled to extend an offer for the Staff Backend Engineer position at Stripe!",
        "body_plain": "Dear Akshit,\n\nOn behalf of everyone at Stripe, we are thrilled to formally extend an offer of employment for the position of Staff Backend Engineer in Seattle/Remote!\n\nBase Salary: $235,000\nEquity: $400,000 RSU over 4 years\nSign-on Bonus: $30,000\n\nPlease review the attached offer letter and let us know your decision by next Monday.\n\nWarm regards,\nSarah Connor"
    },

    # -------------------------------------------------------------
    # 2. DATADOG: Screening & Upcoming Technical Interview
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_datadog_01",
        "gmail_thread_id": "thread_datadog_01",
        "history_id": "1005",
        "sender": "no-reply@datadoghq.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Application Received: Senior Platform Engineer at Datadog",
        "sent_at": days_ago(14),
        "snippet": "Thank you for applying to the Senior Platform Engineer position at Datadog...",
        "body_plain": "Hello Akshit,\n\nThank you for your application to Datadog for the Senior Platform Engineer role. We are reviewing your background and will reach out if there is a match.\n\nDatadog Talent Acquisition"
    },
    {
        "gmail_message_id": "msg_datadog_02",
        "gmail_thread_id": "thread_datadog_01",
        "history_id": "1006",
        "sender": "alex.chen@datadoghq.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Datadog Interview Confirmation: Technical Architecture Round",
        "sent_at": days_ago(3),
        "snippet": "Your upcoming interview with Datadog is scheduled for Friday at 3:00 PM...",
        "body_plain": "Hi Akshit,\n\nYour next interview round with our Engineering Director Alex Chen is confirmed:\n\nDate: This Friday\nTime: 3:00 PM - 4:00 PM EST\nVideo link: https://meet.google.com/abc-defg-hij\nTopic: Distributed Systems & Architecture Deep Dive\n\nPlease prepare a 10-minute overview of a recent project you led.\n\nBest,\nAlex Chen\nEngineering Director, Datadog"
    },

    # -------------------------------------------------------------
    # 3. GOOGLE: Inbound Recruiter Outreach (Recruiter Lead)
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_google_01",
        "gmail_thread_id": "thread_google_01",
        "history_id": "1007",
        "sender": "m.jordan@google.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Exciting Engineering Opportunities at Google Cloud",
        "sent_at": days_ago(7),
        "snippet": "I came across your GitHub and open source work and wanted to connect regarding Staff roles at Google...",
        "body_plain": "Hi Akshit,\n\nI hope you're having a great week! My name is Michael Jordan and I'm a Senior Recruiter on the Google Cloud Infrastructure team.\n\nI was really impressed by your background in asynchronous queue processing and scalability. We are actively hiring Staff Software Engineers for our Cloud Storage team in Mountain View and New York.\n\nAre you open to exploring new roles? If so, I'd love to share more details over a quick call.\n\nBest,\nMichael Jordan\nGoogle Cloud Talent Team"
    },

    # -------------------------------------------------------------
    # 4. META: Application & Polite Rejection
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_meta_01",
        "gmail_thread_id": "thread_meta_01",
        "history_id": "1008",
        "sender": "careers@meta.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Your application to Meta - Production Engineer",
        "sent_at": days_ago(28),
        "snippet": "Thank you for applying to Meta for the Production Engineer opening...",
        "body_plain": "Thank you for your interest in Meta. We have received your application for Production Engineer.\n\nMeta Recruiting"
    },
    {
        "gmail_message_id": "msg_meta_02",
        "gmail_thread_id": "thread_meta_01",
        "history_id": "1009",
        "sender": "careers@meta.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Update regarding your application with Meta",
        "sent_at": days_ago(12),
        "snippet": "Thank you for taking the time to speak with our team. At this time we have decided to pursue other candidates...",
        "body_plain": "Hi Akshit,\n\nThank you for giving us the opportunity to consider your background for the Production Engineer position at Meta.\n\nAfter careful consideration, we have decided to move forward with other candidates whose experience more closely matches the immediate requirements of this role.\n\nWe encourage you to apply for other roles in the future.\n\nSincerely,\nMeta Recruiting Team"
    },

    # -------------------------------------------------------------
    # 5. ANTHROPIC: Take-home Assessment with specific deadline
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_anthropic_01",
        "gmail_thread_id": "thread_anthropic_01",
        "history_id": "1010",
        "sender": "hiring@anthropic.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Anthropic AI Systems: Practical Engineering Assessment",
        "sent_at": days_ago(4),
        "snippet": "Thank you for your application to Anthropic. Please find your practical assessment link below...",
        "body_plain": "Hello Akshit,\n\nThank you for applying to the Systems Engineer role at Anthropic.\n\nAs the next step, please complete the practical coding assignment found here:\nhttps://github.com/anthropic-evals/challenge-systems-7782\n\nPlease submit your solution via a private GitHub repository before Sunday at 11:59 PM UTC.\n\nBest,\nAnthropic Talent Team"
    },

    # -------------------------------------------------------------
    # 6. NOISE / UNRELATED: Marketing, newsletters, order receipts (Must be filtered out)
    # -------------------------------------------------------------
    {
        "gmail_message_id": "msg_spam_01",
        "gmail_thread_id": "thread_spam_01",
        "history_id": "1011",
        "sender": "newsletter@medium.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Top 10 Python libraries you should know in 2026",
        "sent_at": days_ago(2),
        "snippet": "Explore the trending Python open-source tools this week...",
        "body_plain": "Hi reader,\nHere are the top stories on programming and machine learning today..."
    },
    {
        "gmail_message_id": "msg_spam_02",
        "gmail_thread_id": "thread_spam_02",
        "history_id": "1012",
        "sender": "auto-confirm@amazon.com",
        "recipients": ["owner@relayn.local"],
        "subject": "Your Amazon.com order #112-9847123 has shipped",
        "sent_at": days_ago(1),
        "snippet": "Your package is on its way. Track your package at amazon.com...",
        "body_plain": "Hello,\nYour package with Ergonomic Mechanical Keyboard will arrive tomorrow by 8:00 PM."
    }
]

# Generate additional variations (up to 50 total) for rich pipeline testing
COMPANIES = [
    ("Snowflake", "Staff Distributed Systems Engineer", "recruiter.eva@snowflake.com", "Eva Green"),
    ("OpenAI", "Inference Infrastructure Engineer", "talent@openai.com", "Talent Team"),
    ("Uber", "Senior Backend Engineer - Core Services", "hiring@uber.com", "Uber Careers"),
    ("Airbnb", "Staff Fullstack Engineer", "dan.m@airbnb.com", "Dan Miller"),
    ("Linear", "Founding Backend Engineer", "karri@linear.app", "Karri Saarinen"),
    ("Figma", "Systems Reliability Engineer", "recruiting@figma.com", "Figma Talent"),
    ("Vercel", "Edge Runtime Engineer", "lee@vercel.com", "Lee Robinson"),
    ("Notion", "Infrastructure Engineer", "jobs@makenotion.com", "Notion People"),
    ("Coinbase", "Crypto Backend Engineer", "brian@coinbase.com", "Brian K"),
    ("Cloudflare", "Workers Runtime Engineer", "jobs@cloudflare.com", "Cloudflare Careers"),
]

history_counter = 1013
for i, (comp, role, email_addr, recruiter_name) in enumerate(COMPANIES):
    tid = f"thread_synth_{i:02d}"
    # Application confirmation
    SYNTHETIC_EMAILS.append({
        "gmail_message_id": f"msg_synth_app_{i:02d}",
        "gmail_thread_id": tid,
        "history_id": str(history_counter),
        "sender": email_addr,
        "recipients": ["owner@relayn.local"],
        "subject": f"Application Received: {role} at {comp}",
        "sent_at": days_ago(20 - i),
        "snippet": f"Thank you for applying to {comp} for the position of {role}...",
        "body_plain": f"Hello Akshit,\n\nThank you for applying for {role} at {comp}. We have received your materials and will review them shortly.\n\nBest,\n{comp} Recruiting"
    })
    history_counter += 1

    # Outreach or followup
    if i % 2 == 0:
        SYNTHETIC_EMAILS.append({
            "gmail_message_id": f"msg_synth_followup_{i:02d}",
            "gmail_thread_id": tid,
            "history_id": str(history_counter),
            "sender": email_addr,
            "recipients": ["owner@relayn.local"],
            "subject": f"Next steps with {comp} ({role})",
            "sent_at": days_ago(15 - i),
            "snippet": f"Hi Akshit, {recruiter_name} here from {comp}. We'd love to schedule a quick call...",
            "body_plain": f"Hi Akshit,\n\nI reviewed your resume for the {role} role and would love to chat. Could you share your availability for early next week?\n\nThanks,\n{recruiter_name}"
        })
        history_counter += 1
    elif i % 3 == 0:
        SYNTHETIC_EMAILS.append({
            "gmail_message_id": f"msg_synth_rej_{i:02d}",
            "gmail_thread_id": tid,
            "history_id": str(history_counter),
            "sender": email_addr,
            "recipients": ["owner@relayn.local"],
            "subject": f"Update on your application with {comp}",
            "sent_at": days_ago(10 - i),
            "snippet": f"Thank you for considering {comp}. Unfortunately we will not be moving forward...",
            "body_plain": f"Dear Akshit,\n\nThank you for taking the time to explore opportunities with {comp}. At this time, we have chosen to move forward with other candidates.\n\nBest regards,\n{comp} Talent Team"
        })
        history_counter += 1

# Write to tests/fixtures/synthetic_emails.json
output_path = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures" / "synthetic_emails.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(SYNTHETIC_EMAILS, f, indent=2)

print(f"Generated {len(SYNTHETIC_EMAILS)} synthetic emails in {output_path}")
