import pandas as pd
import random

texts_high = [
    "Indemnify against all claims", "liable for any damages", "waive all rights to sue",
    "shall be held harmless from any and all claims", "immediate termination without cause",
    "non-compete for 10 years", "binding arbitration with no appeal",
    "exclusive jurisdiction in foreign country", "unlimited liability", "penalty for late payment of 50%"
]
texts_medium = [
    "subject to change with 30 days notice", "confidentiality survives termination",
    "net 60 days payment terms", "must notify within 48 hours",
    "limitation of liability up to contract value", "governing law of New York",
    "force majeure clause includes pandemics", "standard non-disclosure agreement",
    "intellectual property rights retained", "subcontracting permitted with approval"
]
texts_low = [
    "this agreement is between", "the parties agree as follows", "effective date of this contract",
    "signed by authorized representatives", "contact information for notices",
    "definitions of terms used", "standard office lease agreement",
    "employee handbook acknowledgment", "website terms of service", "cookie policy consent"
]

data = []
for _ in range(700):
    choice = random.choice(['High', 'Medium', 'Low'])
    if choice == 'High':
        data.append({'text': random.choice(texts_high) + " " + random.choice(texts_high), 'risk_level': choice})
    elif choice == 'Medium':
        data.append({'text': random.choice(texts_medium) + " " + random.choice(texts_medium), 'risk_level': choice})
    else:
        data.append({'text': random.choice(texts_low) + " " + random.choice(texts_low), 'risk_level': choice})

df = pd.DataFrame(data)
df.to_csv('data/legal_data.csv', index=False)
print("Created data/legal_data.csv with 700 rows")
