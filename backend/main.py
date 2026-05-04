import os
import joblib
import pytesseract
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
import re
from PIL import Image
try:
    from pdf2image import convert_from_bytes
except ImportError:
    pass # handle later
try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

app = FastAPI(title="LegalShield AI Brain")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize paths
MODEL_PATH = os.path.join(os.path.dirname(__file__), '../model/legal_model.joblib')
VECTORIZER_PATH = os.path.join(os.path.dirname(__file__), '../model/vectorizer.joblib')

model = None
vectorizer = None

@app.on_event("startup")
def load_model():
    global model, vectorizer
    import subprocess
    import sys
    model_loaded = False
    if os.path.exists(MODEL_PATH) and os.path.exists(VECTORIZER_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            vectorizer = joblib.load(VECTORIZER_PATH)
            if hasattr(model, 'classes_'):
                print("Legal Brain Model Loaded!")
                model_loaded = True
            else:
                print("Loaded model is not a trained estimator (no classes_ attribute).")
        except Exception as e:
            print(f"Error loading model: {e}")
            
    if not model_loaded:
        print("Model not found or not trained! Training the model automatically...")
        train_script = os.path.join(os.path.dirname(__file__), '../model/train_model.py')
        try:
            subprocess.run([sys.executable, train_script], check=True)
            model = joblib.load(MODEL_PATH)
            vectorizer = joblib.load(VECTORIZER_PATH)
            if hasattr(model, 'classes_'):
                print("Legal Brain Model Loaded after training!")
            else:
                print("Newly trained model still lacks classes_ attribute.")
        except Exception as e:
            print(f"Failed to train model: {e}")

# Expert Legal Dictionary with 50+ patterns
LEGAL_DICTIONARY = [
    {
        "pattern": r"indemnify\s+and\s+hold\s+harmless",
        "standard_explanation": "Requires you to assume liability for the other party's losses and legal fees in case of a dispute.",
        "eli5_translation": "🛡️ You take the blame and pay the bills if they get sued! 💸",
        "risk_score": 9
    },
    {
        "pattern": r"limitation\s+of\s+liability",
        "standard_explanation": "Caps the amount of money you can recover if the other party breaches the contract.",
        "eli5_translation": "🛑 Even if they ruin everything, they only pay a tiny amount back! 📉",
        "risk_score": 7
    },
    {
        "pattern": r"binding\s+arbitration",
        "standard_explanation": "Forces you to resolve disputes privately with an arbitrator, waiving your right to a jury trial.",
        "eli5_translation": "⚖️ No court for you! You have to use their private judge. 🚫👨‍⚖️",
        "risk_score": 6
    },
    {
        "pattern": r"force\s+majeure",
        "standard_explanation": "Excuses a party from performing their obligations due to unforeseeable, unavoidable events (e.g., natural disasters).",
        "eli5_translation": "🌪️ If an act of God happens, they don't have to do their job! 🌩️",
        "risk_score": 3
    },
    {
        "pattern": r"termination\s+for\s+convenience",
        "standard_explanation": "Allows the other party to cancel the contract at any time without needing a valid reason.",
        "eli5_translation": "✂️ They can dump you anytime for NO reason! 💔",
        "risk_score": 8
    },
    {
        "pattern": r"non-compete",
        "standard_explanation": "Restricts you from working for competitors or starting a similar business for a set period.",
        "eli5_translation": "⛓️ You can't work in the same industry after you leave! 🛑",
        "risk_score": 9
    },
    {
        "pattern": r"intellectual\s+property\s+assignment",
        "standard_explanation": "Transfers ownership of anything you create or invent to the company.",
        "eli5_translation": "🧠 Everything you invent belongs to THEM, not you! 🏭",
        "risk_score": 8
    },
    {
        "pattern": r"automatic\s+renewal",
        "standard_explanation": "The contract will automatically extend for another term unless you opt out within a strict timeframe.",
        "eli5_translation": "🔄 They will keep charging you forever unless you cancel in time! 💳",
        "risk_score": 5
    },
    {
        "pattern": r"exclusive\s+jurisdiction",
        "standard_explanation": "Dictates exactly which state or country's laws apply, and where you must go if you sue.",
        "eli5_translation": "🗺️ If you want to sue them, you have to travel to their home turf! ✈️",
        "risk_score": 6
    },
    {
        "pattern": r"liquidated\s+damages",
        "standard_explanation": "Sets a predetermined financial penalty if you breach the contract, regardless of actual harm.",
        "eli5_translation": "💰 If you mess up, you owe them a huge set amount of cash! 💸",
        "risk_score": 8
    },
    {
        "pattern": r"as\s+is",
        "standard_explanation": "Disclaims all implied warranties; you accept the product or service with all its faults.",
        "eli5_translation": "🗑️ What you see is what you get, even if it's broken! No refunds! 🚫",
        "risk_score": 7
    },
    {
        "pattern": r"time\s+is\s+of\s+the\s+essence",
        "standard_explanation": "Makes strict adherence to deadlines a material term; any delay is a breach of contract.",
        "eli5_translation": "⏰ If you are even 1 minute late, you break the contract! 🏃‍♂️💨",
        "risk_score": 6
    },
    {
        "pattern": r"severability",
        "standard_explanation": "If one clause is found invalid by a court, the rest of the contract remains enforceable.",
        "eli5_translation": "🧩 If one piece of the contract is bad, the rest still counts! ✅",
        "risk_score": 2
    },
    {
        "pattern": r"entire\s+agreement",
        "standard_explanation": "States that the written contract is the final agreement, overriding any prior oral promises.",
        "eli5_translation": "🤐 Only what is written counts. Verbal promises mean NOTHING! 📝",
        "risk_score": 4
    },
    {
        "pattern": r"waiver\s+of\s+jury\s+trial",
        "standard_explanation": "You give up your constitutional right to have a dispute decided by a jury.",
        "eli5_translation": "🧑‍⚖️ You give up your right to a jury! A single judge decides your fate! ⚖️",
        "risk_score": 7
    },
    {
        "pattern": r"joint\s+and\s+several\s+liability",
        "standard_explanation": "Allows the creditor to sue any one party for the entire amount of a shared debt.",
        "eli5_translation": "👯‍♂️ If your partner doesn't pay, you have to pay THEIR share too! 💳",
        "risk_score": 8
    },
    {
        "pattern": r"non-disparagement",
        "standard_explanation": "Prohibits you from making negative comments or reviews about the company.",
        "eli5_translation": "🤐 You can NEVER say anything bad about them online! 🚫🗣️",
        "risk_score": 5
    },
    {
        "pattern": r"at-will\s+employment",
        "standard_explanation": "Allows the employer to fire you at any time, for any legal reason, without notice.",
        "eli5_translation": "🔥 They can fire you anytime, for almost no reason! 🚪",
        "risk_score": 6
    },
    {
        "pattern": r"right\s+of\s+first\s+refusal",
        "standard_explanation": "Gives a party the right to match an offer before an asset or opportunity is sold to a third party.",
        "eli5_translation": "👀 They get the first chance to buy it before you can sell it to anyone else! 🤝",
        "risk_score": 4
    },
    {
        "pattern": r"best\s+efforts",
        "standard_explanation": "Requires a high standard of diligence to fulfill an obligation, though not a strict guarantee.",
        "eli5_translation": "💦 You have to try your absolute hardest, no slacking! 🏋️",
        "risk_score": 5
    },
    # Generating 30 more simple ones to hit the 50+ mark
    {"pattern": r"attorney.?s\s+fees", "standard_explanation": "Loser pays winner's legal costs.", "eli5_translation": "🧑‍⚖️ If you lose in court, you pay THEIR lawyers! 💸", "risk_score": 7},
    {"pattern": r"moral\s+rights", "standard_explanation": "Waives right to attribution and right to object to modifications of your work.", "eli5_translation": "🎨 They can change your art and not even give you credit! 🎭", "risk_score": 6},
    {"pattern": r"subcontracting", "standard_explanation": "Allows them to hire others to do the work without asking you.", "eli5_translation": "👥 They can pass your work off to random strangers! 🤷‍♂️", "risk_score": 4},
    {"pattern": r"audit\s+rights", "standard_explanation": "Gives them the right to inspect your records.", "eli5_translation": "🕵️‍♂️ They can snoop through your files whenever they want! 📂", "risk_score": 5},
    {"pattern": r"change\s+in\s+control", "standard_explanation": "Triggers actions if the company is sold.", "eli5_translation": "🏢 If the company is sold, things might change fast! 🔄", "risk_score": 3},
    {"pattern": r"confidentiality", "standard_explanation": "Requires you to keep information secret.", "eli5_translation": "🤫 Keep your mouth shut! It's a secret! 🤐", "risk_score": 5},
    {"pattern": r"cumulative\s+remedies", "standard_explanation": "Allows a party to use multiple legal remedies at once.", "eli5_translation": "🔨 They can hit you with every legal weapon they have! ⚔️", "risk_score": 6},
    {"pattern": r"default", "standard_explanation": "Defines what constitutes a breach of the agreement.", "eli5_translation": "🚨 Here is exactly how you can mess up and get in trouble! ⚠️", "risk_score": 5},
    {"pattern": r"escalation", "standard_explanation": "Requires disputes to go to senior management before a lawsuit.", "eli5_translation": "📈 You have to talk to the boss before you can sue! 👔", "risk_score": 3},
    {"pattern": r"exclusivity", "standard_explanation": "Prevents you from working with their competitors.", "eli5_translation": "💍 You are married to them! No dating other companies! 🚫", "risk_score": 7},
    {"pattern": r"further\s+assurances", "standard_explanation": "Requires you to do whatever else is needed later to complete the deal.", "eli5_translation": "📝 You promise to sign more stuff later if they need you to! 🖋️", "risk_score": 2},
    {"pattern": r"governing\s+law", "standard_explanation": "Specifies which laws apply to the contract.", "eli5_translation": "📜 The rules of a specific state apply here! 🏛️", "risk_score": 4},
    {"pattern": r"guaranty", "standard_explanation": "Makes you personally responsible for a company debt.", "eli5_translation": "🤝 If your company goes broke, YOU personally pay! 🏚️", "risk_score": 9},
    {"pattern": r"injunctive\s+relief", "standard_explanation": "Allows them to get a court order to stop you from doing something.", "eli5_translation": "🛑 They can get a judge to literally freeze your actions! 🧊", "risk_score": 7},
    {"pattern": r"integration", "standard_explanation": "Means this document is the whole deal.", "eli5_translation": "📦 This paper is everything. No outside promises! 🚫", "risk_score": 3},
    {"pattern": r"modifications", "standard_explanation": "How the contract can be changed.", "eli5_translation": "✏️ If they want to change the rules, this is how they do it. 🔄", "risk_score": 4},
    {"pattern": r"net\s+payment\s+terms", "standard_explanation": "When you have to pay (e.g., Net 30).", "eli5_translation": "📅 You have a set number of days to pay the bill! ⏳", "risk_score": 3},
    {"pattern": r"no\s+implied\s+waiver", "standard_explanation": "If they don't enforce a rule once, they can still enforce it later.", "eli5_translation": "👀 Just because they let you slide once, doesn't mean they will again! 🚔", "risk_score": 5},
    {"pattern": r"notices", "standard_explanation": "How official communication must be sent.", "eli5_translation": "📬 This is where you send the official mail! ✉️", "risk_score": 1},
    {"pattern": r"power\s+of\s+attorney", "standard_explanation": "Gives them the right to sign documents for you.", "eli5_translation": "✍️ They can literally sign your name for you! 😱", "risk_score": 8},
    {"pattern": r"privacy\s+policy", "standard_explanation": "How they use your data.", "eli5_translation": "🕵️ This is what they do with your personal info! 💻", "risk_score": 5},
    {"pattern": r"representations\s+and\s+warranties", "standard_explanation": "Promises that certain facts are true.", "eli5_translation": "🤞 You pinky promise that what you said is true! 🤥", "risk_score": 6},
    {"pattern": r"set-off", "standard_explanation": "Allows them to deduct what you owe them from what they owe you.", "eli5_translation": "➖ They can keep your money if you owe them money! 💸", "risk_score": 5},
    {"pattern": r"specific\s+performance", "standard_explanation": "A court can force you to do what you promised, not just pay damages.", "eli5_translation": "🤖 A judge can literally FORCE you to do the work! ⚒️", "risk_score": 7},
    {"pattern": r"subrogation", "standard_explanation": "Allows their insurance to sue you if you caused the damage.", "eli5_translation": "🛡️ Their insurance company can come after you for cash! 🚔", "risk_score": 6},
    {"pattern": r"survival", "standard_explanation": "Some rules still apply even after the contract ends.", "eli5_translation": "🧟‍♂️ Some of these rules stay alive even after the contract dies! 🪦", "risk_score": 5},
    {"pattern": r"third-party\s+beneficiary", "standard_explanation": "Someone not signing this contract gets rights under it.", "eli5_translation": "👽 Some random third person gets benefits from your deal! 🎁", "risk_score": 4},
    {"pattern": r"venue", "standard_explanation": "The specific court where you have to sue.", "eli5_translation": "🏟️ This is the exact building you have to fight them in! 🏛️", "risk_score": 4},
    {"pattern": r"work\s+made\s+for\s+hire", "standard_explanation": "You don't own the copyright to the work you create for them.", "eli5_translation": "🎨 You made it, but they completely own it! 🛍️", "risk_score": 8},
    {"pattern": r"data\s+processing", "standard_explanation": "How they handle your data under GDPR/CCPA.", "eli5_translation": "💻 How they munch on your personal data! 🍪", "risk_score": 5},
]

SIMPLE_MAP = {
    'indemnify and hold harmless': 'take the blame and pay for damages',
    'indemnify': 'pay for damages',
    'hold harmless': 'take the blame',
    'indemnification': 'paying for damages',
    'limitation of liability': 'cap on how much we pay',
    'liability': 'responsibility to pay',
    'indirect, incidental, or consequential damages': 'extra unexpected costs',
    'binding arbitration': 'a private judge instead of a real court',
    'arbitration': 'a private judge',
    'trial by jury': 'court trial',
    'force majeure': 'act of god (like a hurricane)',
    'acts of god': 'uncontrollable events',
    'terminate this agreement at any time for any reason': 'cancel anytime without reason',
    'termination for convenience': 'canceling just because',
    'non-compete': 'ban on working for competitors',
    'competitor': 'rival company',
    'intellectual property': 'ideas and inventions',
    'perpetual, royalty-free license': 'free use forever',
    'assigned to the employer': 'given to the boss',
    'automatically renew': 'keep charging you automatically',
    'governed by the laws': 'follows the rules',
    'exclusive jurisdiction and venue': 'forced location for lawsuits'
}

class TextRequest(BaseModel):
    text: str

def _risk_score_from_level(level: str) -> int:
    lvl = str(level or "").lower()
    if "high" in lvl:
        return 85
    if "medium" in lvl:
        return 60
    if "low" in lvl:
        return 35
    if "safe" in lvl:
        return 15
    return 50

def _compute_risk_score(text: str, overall_risk: str, found_clauses: list) -> int:
    score = _risk_score_from_level(overall_risk)
    try:
        clause_max_10 = max([int(c.get("risk_score", 0)) for c in found_clauses], default=0)
        score = max(score, clause_max_10 * 10)
    except Exception:
        pass
    return max(0, min(100, int(score)))

def _simple_eli5_from_text(text: str) -> str:
    """
    Lightweight, deterministic "plain English" rewrite (no LLM).
    Uses sentence chopping + a few safe substitutions. Adds emojis to match UI spec.
    """
    t = (text or "").strip()
    if not t:
        return ""

    # Normalize whitespace
    t = re.sub(r"\s+", " ", t)

    # Gentle substitutions (avoid changing legal meaning too aggressively)
    replacements = {
        r"\bshall\b": "must",
        r"\bhereby\b": "",
        r"\bthereof\b": "of it",
        r"\btherein\b": "in it",
        r"\bnotwithstanding\b": "even if",
        r"\bpursuant to\b": "under",
        r"\bprior to\b": "before",
        r"\bcommence\b": "start",
        r"\bterminate\b": "end",
        r"\bincluding\b": "like",
    }
    for pattern, repl in replacements.items():
        t = re.sub(pattern, repl, t, flags=re.IGNORECASE)

    # Split into short bullets (max ~6)
    parts = re.split(r"(?<=[\.\!\?])\s+", t)
    bullets = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        bullets.append(p)
        if len(bullets) >= 6:
            break

    # If sentence splitting fails, just take a chunk
    if not bullets:
        bullets = [t[:600].strip()]

    # Emoji-rich but readable
    emoji = ["🧾", "👀", "⚠️", "💬", "🛡️", "✅"]
    lines = []
    for i, b in enumerate(bullets):
        lines.append(f"{emoji[i % len(emoji)]} {b}")
    return "\n".join(lines).strip()

def extract_rental_details(text: str):
    details = {}
    
    # Notice Period (Clause 11 / 15)
    notice_match = re.search(r'(one|two|three|\d+)\s+months?\s+prior\s+notice', text, re.IGNORECASE)
    if notice_match:
        details['notice_period'] = notice_match.group(1).lower() + " month(s)"
    else:
        alt_match = re.search(r'notice\s+period.*?(\d+)\s+month', text, re.IGNORECASE)
        if alt_match:
            details['notice_period'] = alt_match.group(1) + " month(s)"
        
    # Rent and Deposit
    rent_match = re.search(r'(?:rent|monthly rent).*?(?:Rs\.?|INR)\s*([\d,]+)', text, re.IGNORECASE)
    if rent_match:
        details['monthly_rent'] = rent_match.group(1)
    elif re.search(r'rent of Rs\.\s*\(Amount', text, re.IGNORECASE):
        details['monthly_rent'] = "TBD"
        
    deposit_match = re.search(r'security deposit.*?(?:Rs\.?|INR)\s*([\d,]+)', text, re.IGNORECASE)
    if deposit_match:
        details['security_deposit'] = deposit_match.group(1)
    elif re.search(r'security deposit of Rs\.\s*\(Amount', text, re.IGNORECASE):
        details['security_deposit'] = "TBD"
        
    # Penalty
    if re.search(r'(2x|double|twice|two times).*?rent', text, re.IGNORECASE) or re.search(r'rent.*?twice', text, re.IGNORECASE) or re.search(r'double.*?penalty', text, re.IGNORECASE):
        details['penalty'] = "2x Rent Penalty"
        
    # Inventory
    fans_match = re.search(r'Fans?\s*[:-]?\s*(\d+)', text, re.IGNORECASE)
    if fans_match: 
        details['fans'] = fans_match.group(1)
    elif "Number of Fans" in text:
        details['fans'] = "TBD"
        
    lights_match = re.search(r'(?:Tube\s*|CFL\s*)?Lights?\s*[:-]?\s*(\d+)', text, re.IGNORECASE)
    if lights_match: 
        details['lights'] = lights_match.group(1)
    elif "Number of CFL Lights" in text or "Number of Tube Lights" in text:
        details['lights'] = "TBD"
        
    geysers_match = re.search(r'Geysers?\s*[:-]?\s*(\d+)', text, re.IGNORECASE)
    if geysers_match: 
        details['geysers'] = geysers_match.group(1)
    elif "Number of Geyser" in text:
        details['geysers'] = "TBD"
        
    # Key Dates
    rent_due_match = re.search(r'(?:rent|payable)\s+(?:on\s+or\s+before|by)\s+the\s+(\d+(?:st|nd|rd|th)?(?:[- ]day)?)', text, re.IGNORECASE)
    if not rent_due_match:
        rent_due_match = re.search(r'(?:payable|due)\s+on\s+(\d+(?:st|nd|rd|th)?)', text, re.IGNORECASE)
    if rent_due_match:
        details['rent_due_date'] = rent_due_match.group(1).strip() + " of month"
    elif re.search(r'rent.*?5th', text, re.IGNORECASE):
        details['rent_due_date'] = "5th of month"
    else:
        details['rent_due_date'] = "TBD"

    expiry_match = re.search(r'(?:expiry|end\s+date|expires\s+on)\s*(?::|-)?\s*(\d{1,2}[a-z]{0,2}\s+[a-zA-Z]+\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
    if expiry_match:
        details['expiry_date'] = expiry_match.group(1)
    else:
        details['expiry_date'] = "TBD"
    
    return details

def extract_entities(text: str):
    promoter_name = "Not Specified"
    allottee_name = "Not Specified"
    
    def clean_entity(name_part):
        if not name_part:
            return None
        clean_name = re.sub(r'[\W_]+', '', name_part.lower())
        if re.search(r'\.{4,}|_{3,}', name_part) or clean_name in ['the', 'ofthe', 'schedule', 'and', 'this']:
            return None
        return name_part.strip()[:50]
        
    promoter_match = re.search(r'(.*?)(?:hereinafter\s+referred\s+to\s+as\s+(?:the\s+)?[\'"]?Promoter[\'"]?)', text, re.IGNORECASE)
    if promoter_match:
        name_part = " ".join(promoter_match.group(1).split()[-5:])
        res = clean_entity(name_part)
        if res: promoter_name = res
            
    allottee_match = re.search(r'(.*?)(?:hereinafter\s+referred\s+to\s+as\s+(?:the\s+)?[\'"]?Allottee[\'"]?)', text, re.IGNORECASE)
    if allottee_match:
        name_part = " ".join(allottee_match.group(1).split()[-5:])
        res = clean_entity(name_part)
        if res: allottee_name = res

    return {
        "promoter_name": promoter_name,
        "allottee_name": allottee_name
    }

def extract_deadlines(text: str):
    deadlines = []
    date_matches = re.finditer(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-zA-Z]*\s+\d{4})\b', text, re.IGNORECASE)
    seen = set()
    for m in date_matches:
        d = m.group(1)
        if d not in seen:
            seen.add(d)
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 30)
            context = text[start:end].replace('\n', ' ').strip()
            deadlines.append({"date": d, "context": context})
    return deadlines

def generate_counter_proposals(keywords_found):
    counters = []
    for kw in keywords_found:
        if 'indemnify' in kw.lower() or 'hold harmless' in kw.lower():
            counters.append("Counter-Clause: Both parties shall mutually indemnify each other against direct damages arising out of gross negligence.")
        if 'liability' in kw.lower():
            counters.append("Counter-Clause: The total liability of either party shall not exceed the total fees paid under this agreement in the preceding 12 months.")
        if 'arbitration' in kw.lower():
            counters.append("Counter-Clause: Any dispute shall be settled by mediation first. If unresolved, parties submit to the exclusive jurisdiction of the local courts.")
        if 'non-compete' in kw.lower():
            counters.append("Counter-Clause: The non-compete obligation shall be restricted to a period of 6 months and limited to the client's direct competitors.")
        if 'perpetuity' in kw.lower():
            counters.append("Counter-Clause: The confidentiality obligations shall survive for a period of 2 years post-termination.")
            
    if not counters:
        counters.append("Counter-Clause: This agreement seems standard. No critical counter-proposals generated.")
        
    return list(dict.fromkeys(counters))

def generate_negotiation_toolkit(details, doc_type, keywords):
    toolkit = []
    if doc_type == "Real Estate Mode":
        if 'possession_date' in details and "Blank in Document" in details['possession_date']:
            toolkit.append("The Possession Date is blank in your agreement. Can we fix this to [Date] before signing?")
        if details.get('defect_liability_risk'):
            toolkit.append("The 5-year structural warranty is missing or reduced. Please update Clause 14 to match RERA standards.")
        if 'payment_plan' in details and "Blank in Document" in details['payment_plan']:
            toolkit.append("The Payment Milestones are not specified. Please attach the construction-linked payment schedule.")
            
    kw_str = " ".join(keywords).lower()
    if 'indemnify' in kw_str:
        toolkit.append("Draft an email proposing that the indemnification clause must be mutual.")
    if 'liability' in kw_str:
        toolkit.append("Request a specific cap on liability (e.g., total fees paid).")
        
    if len(toolkit) < 3:
        toolkit.append("Request a general review meeting to clarify ambiguous clauses.")
        toolkit.append("Ask for an explicit timeline on when the penalty clauses can be triggered.")
        
    return list(dict.fromkeys(toolkit))[:3]

def validate_field(val):
    if not val: return 'Not Specified / Blank in Document'
    if re.search(r'\.{3,}|_{3,}', val):
        return 'Not Specified / Blank in Document'
    return val.strip()

def extract_universal_details(text: str):
    details = {}
    
    text_lower = text.lower()
    if any(k in text_lower for k in ['promoter', 'allottee', 'rera']):
        details['doc_type'] = "Real Estate Mode"
    elif any(k in text_lower for k in ['confidentiality', 'non-disclosure']):
        details['doc_type'] = "NDA Mode"
    elif any(k in text_lower for k in ['landlord', 'tenant', 'rent agreement']):
        details['doc_type'] = "Rental Mode"
    else:
        details['doc_type'] = "General Mode"
        
    duration_match = re.search(r'(?:term|duration|valid for).*?(\d+\s+(?:years?|months?|days?)|\.{3,}|_{3,})', text, re.IGNORECASE)
    if duration_match:
        details['duration'] = validate_field(duration_match.group(1))
    else:
        fallback = re.search(r'\b(\d+\s+(?:years?|months?|days?))\b', text, re.IGNORECASE)
        details['duration'] = validate_field(fallback.group(1)) if fallback else "Not Specified / Blank in Document"

    money_match = re.search(r'(?:Rs\.?|INR|\$)\s*([\d,]+(\.\d{2})?|\.{3,}|_{3,})', text, re.IGNORECASE)
    details['money'] = validate_field(money_match.group(0)) if money_match else "Not Specified / Blank in Document"

    term_match = re.search(r'terminat.*?(\d+\s+(?:days?|months?)\s+(?:prior|written)?\s*notice|\.{3,}|_{3,})', text, re.IGNORECASE)
    if term_match:
        details['termination'] = validate_field(term_match.group(1))
    elif "termination for convenience" in text_lower:
        details['termination'] = "At Will / Anytime"
    else:
        details['termination'] = "Standard Breach / Default"

    law_match = re.search(r'(?:governing law|jurisdiction).*?(?:state of|courts of|laws of)\s*([a-zA-Z\s]+|\.{3,}|_{3,})(?:[\.\,]|\n)', text, re.IGNORECASE)
    details['governing_law'] = validate_field(law_match.group(1)) if law_match else "Not Specified / Blank in Document"

    nda_match = re.search(r'(?:penalty|liquidated\s+damages|breach).*?(?:Rs\.?|INR|\$)\s*([\d,]+(\.\d{2})?)', text, re.IGNORECASE)
    if nda_match:
        amount_str = nda_match.group(1).replace(',', '')
        try:
            if float(amount_str) > 100000:
                details['nda_penalty'] = nda_match.group(0)
        except:
            pass

    if details['doc_type'] == "Real Estate Mode":
        possession_match = re.search(r'possession.*?(?:date|by|on)\s*([a-zA-Z0-9\s/,-]+|\.{3,}|_{3,})', text, re.IGNORECASE)
        details['possession_date'] = validate_field(possession_match.group(1)) if possession_match else 'Not Specified / Blank in Document'
        
        defect_match = re.search(r'defect liability.*?(?:period|for)\s*([a-zA-Z0-9\s]+|\.{3,}|_{3,})', text, re.IGNORECASE)
        details['defect_liability'] = validate_field(defect_match.group(1)) if defect_match else 'Not Specified / Blank in Document'
        
        if details['defect_liability'] != 'Not Specified / Blank in Document' and '5' not in details['defect_liability']:
            details['defect_liability_risk'] = True
        else:
            details['defect_liability_risk'] = False
        
        payment_match = re.search(r'payment milestone.*?(schedule|attached|below)', text, re.IGNORECASE)
        details['payment_plan'] = 'Present' if payment_match else 'Not Specified / Blank in Document'

    return details

def extract_clauses_and_risks(text: str):
    # Error Handling & Safety for Non-Legal Documents
    legal_keywords = ['agreement', 'contract', 'party', 'parties', 'hereinafter', 'hereby', 'witnesseth', 'promoter', 'allottee', 'tenant', 'landlord', 'confidentiality', 'disclosure', 'liability', 'indemnify', 'signature', 'clause', 'terms', 'rera']
    if sum(1 for word in legal_keywords if word in text.lower()) < 2 and len(text.split()) < 100:
        return {"error": "Unsupported document type. Please upload a Legal Agreement."}

    found_clauses = []
    keywords_found = []
    
    # Track which keywords exist in the text for simplified replacement
    for complex_term, simple_term in SIMPLE_MAP.items():
        if re.search(r'\b' + re.escape(complex_term) + r'\b', text, re.IGNORECASE):
            keywords_found.append(complex_term)
            
    # Predict risk score
    risk_score = 1
    if model and vectorizer:
        try:
            X_vec = vectorizer.transform([text])
            risk_score = int(model.predict(X_vec)[0])
        except Exception as e:
            print("Model error:", e)

    rental_details = extract_rental_details(text)
    universal_details = extract_universal_details(text)
    is_rental = bool(rental_details.get('monthly_rent') or rental_details.get('security_deposit') or rental_details.get('notice_period') or rental_details.get('penalty'))

    if is_rental and rental_details.get('penalty') == '2x Rent Penalty':
        risk_score = max(risk_score, 8)
    if 'arbitration' in " ".join(keywords_found).lower():
        risk_score = max(risk_score, 8)
        
    is_nda_trap = False
    if re.search(r'non-compete', text, re.IGNORECASE) or re.search(r'perpetuity', text, re.IGNORECASE):
        risk_score = max(risk_score, 10)
        is_nda_trap = True

    # Fallback to dictionary scoring if model fails
    if risk_score == 1:
        for entry in LEGAL_DICTIONARY:
            if re.search(entry["pattern"], text, re.IGNORECASE):
                found_clauses.append(entry)
        if found_clauses:
            risk_score = max([int(c.get("risk_score", 0)) for c in found_clauses], default=1)

    overall_risk = "High Risk" if risk_score >= 7 else "Medium Risk" if risk_score >= 4 else "Low Risk" if risk_score >= 2 else "Safe"

    recommendations = []
    if risk_score >= 4:
        for kw in keywords_found:
            if 'indemnify' in kw.lower() or 'hold harmless' in kw.lower():
                recommendations.append("Ask to make the indemnification mutual.")
            if 'liability' in kw.lower():
                recommendations.append("Request a cap on limitation of liability equal to fees paid.")
            if 'arbitration' in kw.lower():
                recommendations.append("Opt-out of binding arbitration if possible.")
            if 'non-compete' in kw.lower():
                recommendations.append("Negotiate a shorter term or smaller geographic area for the non-compete.")
            if 'intellectual property' in kw.lower() or 'assigned' in kw.lower():
                recommendations.append("Ensure you retain ownership of your pre-existing IP.")
                
        # Default recommendations if no specific keyword matched
        if not recommendations:
            recommendations = [
                "Review the high-risk terms identified.",
                "Consider consulting legal counsel.",
                "Propose a more balanced version of the clauses."
            ]
    else:
        recommendations = [
            "Review the specific terms just in case.",
            "Keep a copy of this for your records.",
            "Ensure the payment terms match your expectations.",
        ]
        
    # Deduplicate and limit to 3
    recommendations = list(dict.fromkeys(recommendations))[:3]

    standard_explanation = text.strip()[:50000] if text else ""
    
    def translate_to_eli5(kws):
        bullets = []
        
        if is_nda_trap:
            bullets.append("⚠️ CRITICAL: You are signing a Non-Compete clause which could block your career for years.")
            
        if universal_details.get('doc_type') == "Real Estate Mode":
            bullets.append("🏗️ Possession: Explain when the builder must hand over the property.")
            bullets.append("🛠️ 5-Year Warranty: Highlight the section where the builder is responsible for structural defects for 5 years.")
            bullets.append("💰 Payment Plan: Summarize the milestone payments (e.g., 30% after agreement, 45% after plinth).")
        elif is_rental:
            if 'monthly_rent' in rental_details:
                bullets.append(f"💰 Rent Details: Your monthly rent is Rs. {rental_details['monthly_rent']}.")
            if 'security_deposit' in rental_details:
                bullets.append(f"🏦 Security Deposit: You need to deposit Rs. {rental_details['security_deposit']}.")
            if 'notice_period' in rental_details:
                bullets.append(f"📅 Notice Period: You must give {rental_details['notice_period']} notice before leaving.")
            if 'penalty' in rental_details:
                bullets.append(f"⚠️ Penalty: Warning! There is a {rental_details['penalty']} if you stay late.")
            if not bullets:
                bullets.append("🏠 Rental Agreement: Standard terms apply.")
        else:
            doc_type = universal_details.get('doc_type', "General Mode")
            if doc_type == "NDA Mode":
                bullets.append("🤫 NDA Mode Detected: This looks like a Non-Disclosure Agreement.")
            else:
                bullets.append(f"📄 I've analyzed this as a {doc_type}. Here are the most important things you are signing...")

            if universal_details.get('duration') and universal_details['duration'] not in ["Not Specified", "Not Specified / Blank in Document"]:
                bullets.append(f"⏱️ Duration: This lasts for {universal_details['duration']}.")
            if universal_details.get('money') and universal_details['money'] not in ["TBD", "Not Specified", "Not Specified / Blank in Document"]:
                bullets.append(f"💰 Money: The payment amount is {universal_details['money']}.")
            if universal_details.get('termination') and universal_details['termination'] != "Standard Breach / Default":
                bullets.append(f"🚪 Termination: You can get out via {universal_details['termination']}.")
            if universal_details.get('governing_law') and universal_details['governing_law'] != "Not Explicit":
                bullets.append(f"🏛️ Governing Law: Disputes are handled in {universal_details['governing_law']}.")

            kw_str = " ".join(kws).lower()
            if "liability" in kw_str:
                bullets.append("⚖️ Money Limit: There is a cap on how much you can sue for (last 12 months of fees).")
            if "class action" in kw_str or "arbitration" in kw_str:
                bullets.append("🚫 No Rights: You cannot join a class-action lawsuit.")
            if "force majeure" in kw_str or "acts of god" in kw_str:
                bullets.append("⚡ Tech Issues: They aren't responsible if the internet or machines break down.")
                
            if len(bullets) <= 1:
                bullets.append("📝 Standard Terms: This document contains standard legal provisions.")
            
        return "\n\n".join(bullets)

    eli5_explanation = translate_to_eli5(keywords_found)

    entities_extracted = extract_entities(text)
    deadlines_extracted = extract_deadlines(text)
    counter_proposals = generate_counter_proposals(keywords_found)
    negotiation_toolkit = generate_negotiation_toolkit(universal_details, universal_details.get('doc_type'), keywords_found)

    def get_critical_clauses():
        clauses = []
        
        if is_rental and rental_details.get('monthly_rent'):
            val = rental_details.get('monthly_rent', '')
            match = re.search(r'[^.\n]*(?:rent|monthly rent)[^.\n]*' + re.escape(val) + r'[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else f"Monthly rent is set at Rs. {val}"
            status = 'Warning' if 'TBD' in val or re.search(r'\.{3,}|_{3,}', val) else 'Safe'
            clauses.append({
                "title": "Rent Payment",
                "original_text": original_text,
                "status": status,
                "analysis": "Specifies the regular payment amount for the lease."
            })
            
        if universal_details.get('doc_type') == 'Real Estate Mode':
            val = universal_details.get('possession_date', '')
            val_esc = re.escape(val)
            if val == 'Not Specified / Blank in Document': val_esc = r'(?:\.{3,}|_{3,})'
            match = re.search(r'[^.\n]*possession[^.\n]*' + val_esc + r'[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else f"Possession Date: {val}"
            status = 'Warning' if 'Not Specified' in val else 'Safe'
            clauses.append({
                "title": "Possession Date",
                "original_text": original_text,
                "status": status,
                "analysis": "Defines the exact date when the property will be handed over."
            })

            val = universal_details.get('defect_liability', '')
            val_esc = re.escape(val)
            if val == 'Not Specified / Blank in Document': val_esc = r'(?:\.{3,}|_{3,})'
            match = re.search(r'[^.\n]*defect liability[^.\n]*' + val_esc + r'[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else f"Defect Liability Period: {val}"
            status = 'Warning' if 'Not Specified' in val or '5' not in val else 'Safe'
            clauses.append({
                "title": "Defect Liability (5 years)",
                "original_text": original_text,
                "status": status,
                "analysis": "Ensures the builder fixes structural defects for 5 years."
            })

            match = re.search(r'[^.\n]*(?:payment milestone|payment schedule|schedule of payment)[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else "Payment Schedule attached as Annexure."
            clauses.append({
                "title": "Payment Milestones",
                "original_text": original_text,
                "status": "Safe" if match else "Warning",
                "analysis": "Dictates when and how much you must pay at each construction stage."
            })

            match = re.search(r'[^.\n]*(?:carpet area)[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else "Any change in carpet area must be adjusted in price."
            clauses.append({
                "title": "Carpet Area Recalculation",
                "original_text": original_text,
                "status": "Caution",
                "analysis": "Ensures you are refunded if the final carpet area is smaller than promised."
            })

            match = re.search(r'[^.\n]*(?:cancel|terminat)[^.\n]*(?:agreement|allotment)[^.\n]*', text, re.IGNORECASE)
            original_text = match.group(0).strip() if match else "Cancellation rules apply as per RERA."
            clauses.append({
                "title": "Cancellation / Termination Rules",
                "original_text": original_text,
                "status": "Warning",
                "analysis": "Specifies conditions under which the builder can cancel your allotment."
            })
            
        sorted_clauses = sorted(found_clauses, key=lambda x: x.get('risk_score', 0), reverse=True)
        
        for clause in sorted_clauses:
            if len(clauses) >= 8: break
            pattern = clause['pattern']
            match = re.search(pattern, text, re.IGNORECASE)
            if not match: continue
            
            start_pos = match.start()
            end_pos = match.end()
            sentence_start = max(text.rfind('.', 0, start_pos), text.rfind('\n', 0, start_pos)) + 1
            sentence_end_dot = text.find('.', end_pos)
            sentence_end_nl = text.find('\n', end_pos)
            if sentence_end_dot == -1: sentence_end_dot = len(text)
            if sentence_end_nl == -1: sentence_end_nl = len(text)
            sentence_end = min(sentence_end_dot, sentence_end_nl) + 1
            original_text = text[sentence_start:sentence_end].strip()
            
            if len(original_text) > 400:
                original_text = text[max(0, start_pos - 100):min(len(text), end_pos + 100)].strip() + "..."
                
            risk_score = clause.get('risk_score', 0)
            status = 'Safe'
            if risk_score >= 8: status = 'Warning'
            elif risk_score >= 5: status = 'Caution'
            
            words = pattern.replace('\\s+', ' ').replace('\\', '').split()
            title = " ".join([w.capitalize() for w in words if w.isalpha()]).replace('S ', 's ')
            if not title: title = "Important Clause"
            if title.lower() in [c['title'].lower() for c in clauses]: continue
            
            clauses.append({
                "title": title,
                "original_text": original_text,
                "status": status,
                "analysis": clause.get('standard_explanation', 'Important legal provision.')
            })
            
        return clauses[:8]

    critical_clauses = get_critical_clauses()

    return {
        "risk_score": risk_score * 10,  # Scale to 0-100 for frontend
        "risk_level": overall_risk,
        "standard_explanation": standard_explanation,
        "eli5_explanation": eli5_explanation,
        "negotiation_tips": recommendations,
        "keywords_found": keywords_found,
        "rental_details": rental_details,
        "universal_details": universal_details,
        "entities": entities_extracted,
        "deadlines": deadlines_extracted,
        "counter_proposals": counter_proposals,
        "negotiation_toolkit": negotiation_toolkit,
        "critical_clauses": critical_clauses
    }

@app.post("/analyze/text")
async def analyze_text(req: TextRequest):
    return extract_clauses_and_risks(req.text)

@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    content = await file.read()
    text = ""
    
    if file.filename.lower().endswith('.pdf'):
        extracted = ""
        # 1. Try PyMuPDF (fitz) directly for text extraction
        if fitz is not None:
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                for page in doc:
                    extracted += (page.get_text() or "") + "\n"
            except Exception as e:
                print("PyMuPDF text extraction error:", e)
                
        # 2. Fallback to pypdf if fitz fails or is missing
        if not extracted.strip() and PdfReader is not None:
            try:
                reader = PdfReader(io.BytesIO(content))
                for page in reader.pages:
                    extracted += (page.extract_text() or "") + "\n"
            except Exception as e:
                print("PDF text extraction error:", e)

        extracted = extracted.strip()
        if extracted:
            text = extracted
        else:
            # 3. Scanned PDF fallback OCR
            if fitz is None:
                return {
                    "error": (
                        "PDF has no selectable text (likely scanned). "
                        "To extract it without Poppler, install `pymupdf` (PyMuPDF). "
                        "Alternatively upload images."
                    )
                }

            try:
                doc = fitz.open(stream=content, filetype="pdf")
                for i in range(len(doc)):
                    page = doc.load_page(i)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    text += pytesseract.image_to_string(img) + "\n"
            except pytesseract.pytesseract.TesseractNotFoundError:
                return {
                    "error": (
                        "Scanned PDF detected and rendered successfully, but Tesseract OCR is not installed or not in PATH. "
                        "Install Tesseract (Windows) and restart the backend, or upload a selectable-text PDF."
                    )
                }
            except Exception as e:
                return {
                    "error": (
                        "Scanned PDF detected. Rendering/OCR failed. "
                        f"{str(e)}"
                    )
                }
    elif file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        try:
            image = Image.open(io.BytesIO(content))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            return {"error": f"Image OCR failed. Ensure tesseract is installed. {str(e)}"}
    else:
        # Assuming plain text file
        text = content.decode('utf-8', errors='ignore')

    return extract_clauses_and_risks(text)

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": model is not None}
