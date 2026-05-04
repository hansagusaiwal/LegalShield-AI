import pandas as pd
import random
import os
import re

# Categories and their definitions
CATEGORIES = ['High Risk', 'Medium Risk', 'Low Risk', 'Safe']

# Complex variations of keywords as requested
KEYWORDS = {
    'Indemnify': [
        "User agrees to indemnify and hold harmless the company from any and all claims.",
        "The customer shall defend, indemnify, and hold harmless the service provider.",
        "Both parties agree to mutually indemnify each other against third-party claims.",
        "We accept no responsibility and you must indemnify us for any loss.",
        "Indemnification obligations shall survive the termination of this agreement."
    ],
    'Limitation of Liability': [
        "Our liability shall not exceed the amount paid by the user in the past 12 months.",
        "In no event shall the company be liable for indirect, incidental, or consequential damages.",
        "The liability of the provider is strictly limited to the direct damages incurred.",
        "To the maximum extent permitted by law, liability is capped at fifty dollars.",
        "Parties agree that the limitation of liability reflects an allocation of risk."
    ],
    'Arbitration': [
        "Any disputes arising under this agreement shall be resolved by binding arbitration.",
        "Parties waive their right to a trial by jury and agree to arbitration.",
        "Arbitration shall take place in a mutually agreed upon jurisdiction.",
        "The costs of arbitration shall be split equally between both parties.",
        "All claims must be arbitrated on an individual basis, and not in a class action."
    ],
    'Force Majeure': [
        "Neither party shall be held liable for failure to perform due to acts of God.",
        "Force majeure events include strikes, lockouts, or other industrial disputes.",
        "In the event of a force majeure, the affected party shall notify the other promptly.",
        "A pandemic or epidemic shall be considered a force majeure event.",
        "Performance is excused to the extent delayed by a force majeure event."
    ],
    'Termination for Convenience': [
        "The company may terminate this agreement at any time for any reason with 30 days notice.",
        "Either party may terminate this contract for convenience upon written notice.",
        "Termination for convenience does not relieve the obligation to pay for services rendered.",
        "We reserve the right to cancel your subscription at our sole discretion.",
        "This contract can be terminated by the provider without cause at any time."
    ],
    'Non-compete': [
        "Employee agrees not to work for a competitor for a period of two years post-employment.",
        "During the term of this agreement and for 12 months thereafter, you will not compete.",
        "The non-compete clause applies within a 50-mile radius of the company headquarters.",
        "User shall not develop a competing product while using our services.",
        "Any breach of this non-compete provision will result in immediate injunctive relief."
    ],
    'IP Assignment': [
        "All intellectual property developed during employment is the sole property of the company.",
        "User grants the platform a worldwide, perpetual, royalty-free license to use their content.",
        "Any inventions, discoveries, or improvements are hereby assigned to the employer.",
        "The creator retains all moral rights, but assigns economic rights to the publisher.",
        "You transfer all copyright, patents, and trademarks developed under this agreement."
    ],
    'Automatic Renewal': [
        "This subscription will automatically renew unless canceled 30 days prior to the term end.",
        "The contract shall automatically renew for successive one-year terms.",
        "Your payment method will be charged automatically at the end of each billing cycle.",
        "To prevent automatic renewal, the user must follow the cancellation procedure outlined.",
        "By agreeing, you consent to continuous automatic renewals without further notice."
    ],
    'Jurisdiction': [
        "This agreement shall be governed by the laws of the State of Delaware.",
        "Any legal action shall be brought exclusively in the courts of New York.",
        "Parties consent to the exclusive jurisdiction and venue of the federal courts.",
        "The governing law shall be the laws of England and Wales.",
        "Disputes shall be resolved in the jurisdiction where the company is registered."
    ]
}

KEYWORD_TO_RISK = {
    'Indemnity': 9,
    'Non-compete': 8,
    'IP Assignment': 8,
    'Termination for Convenience': 7,
    'Limitation of Liability': 6,
    'Arbitration': 6,
    'Automatic Renewal': 5,
    'Jurisdiction': 3,
    'Force Majeure': 2,
}

SIMPLE_MAP = {
    'indemnify': 'pay for damages',
    'hold harmless': 'take the blame',
    'indemnification': 'paying for damages',
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

SAFE_FILLERS = [
    "This document outlines the standard terms of service.",
    "Please read these terms carefully before using the service.",
    "The headings in this document are for convenience only.",
    "If any provision is found invalid, the rest of the agreement remains in effect.",
    "You can contact support at the email address provided below.",
    "We may update these terms from time to time.",
    "Thank you for choosing our product.",
    "The effective date of this agreement is listed at the top.",
    "These terms constitute the entire agreement between the parties.",
    "Notices shall be sent via electronic mail."
]

def _augment(clause: str) -> str:
    if random.random() < 0.35:
        clause = clause + " " + random.choice(SAFE_FILLERS)
    if random.random() < 0.20:
        clause = clause.replace("shall", "will").replace("agreement", "contract")
    return clause

def simplify_text(text: str) -> str:
    simplified = text
    for complex_term, simple_term in SIMPLE_MAP.items():
        pattern = re.compile(re.escape(complex_term), re.IGNORECASE)
        simplified = pattern.sub(simple_term, simplified)
    return simplified

def generate_data(num_rows=1200, seed=42):
    random.seed(seed)
    data = []

    per_class = num_rows // 4
    targets = {
        'High Risk': per_class,
        'Medium Risk': per_class,
        'Low Risk': per_class,
        'Safe': num_rows - (per_class * 3),
    }

    high_keys = [k for k, v in KEYWORD_TO_RISK.items() if v >= 7]
    med_keys = [k for k, v in KEYWORD_TO_RISK.items() if 4 <= v <= 6]
    low_keys = [k for k, v in KEYWORD_TO_RISK.items() if 1 <= v <= 3]

    for _ in range(targets['Safe']):
        clause = _augment(random.choice(SAFE_FILLERS))
        eli5 = simplify_text(clause)
        data.append({'original_text': clause, 'eli5_text': eli5, 'risk_score': 1})

    for _ in range(targets['High Risk']):
        keyword = random.choice(high_keys)
        clause = _augment(random.choice(KEYWORDS[keyword]))
        eli5 = simplify_text(clause)
        data.append({'original_text': clause, 'eli5_text': eli5, 'risk_score': KEYWORD_TO_RISK[keyword]})

    for _ in range(targets['Medium Risk']):
        keyword = random.choice(med_keys)
        clause = _augment(random.choice(KEYWORDS[keyword]))
        eli5 = simplify_text(clause)
        data.append({'original_text': clause, 'eli5_text': eli5, 'risk_score': KEYWORD_TO_RISK[keyword]})

    for _ in range(targets['Low Risk']):
        keyword = random.choice(low_keys)
        clause = _augment(random.choice(KEYWORDS[keyword]))
        eli5 = simplify_text(clause)
        data.append({'original_text': clause, 'eli5_text': eli5, 'risk_score': KEYWORD_TO_RISK[keyword]})

    df = pd.DataFrame(data).sample(frac=1.0, random_state=seed).reset_index(drop=True)

    os.makedirs('../data', exist_ok=True)
    df.to_csv('../data/legal_data.csv', index=False)
    print(f"Generated {len(df)}-row balanced synthetic legal dataset at ../data/legal_data.csv")

if __name__ == "__main__":
    generate_data(1200)
