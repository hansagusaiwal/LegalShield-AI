import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
import re

# Dictionary for mapping complex terms to simple terms
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

def train_and_save_model():
    print("Loading dataset...")
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, 'data', 'legal_data.csv')
    if not os.path.exists(data_path):
        print(f"Dataset not found at {data_path}. Please run generate_dataset.py first.")
        return
        
    df = pd.read_csv(data_path)
    
    # Map risk_level to risk_score (1-10 scale)
    risk_map = {
        'High Risk': 8,
        'Medium Risk': 5,
        'Low Risk': 3,
        'Safe': 1
    }
    
    # We predict risk_score
    X = df['text']
    y = df['risk_level'].map(risk_map).fillna(5)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train Vectorizer
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=8000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    
    # Train Classifier
    print("Training Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced')
    model.fit(X_train_vec, y_train)
    
    y_pred = model.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy:.4f}")
    
    # Save the model and vectorizer
    model_path = os.path.join(base_dir, 'model', 'legal_model.joblib')
    vectorizer_path = os.path.join(base_dir, 'model', 'vectorizer.joblib')
    joblib.dump(model, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    print(f"Model saved as {model_path}")
    print(f"Vectorizer saved as {vectorizer_path}")

if __name__ == '__main__':
    train_and_save_model()
