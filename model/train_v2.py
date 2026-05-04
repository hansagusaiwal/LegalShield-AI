import pandas as pd
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

def main():
    # Define paths
    base_dir = os.path.dirname(os.path.dirname(__file__))
    data_path = os.path.join(base_dir, 'data', 'legal_data.csv')
    model_path = os.path.join(base_dir, 'model', 'legal_risk_model.joblib')
    vectorizer_path = os.path.join(base_dir, 'model', 'vectorizer.joblib')

    # Load the data
    print(f"Loading data from {data_path}...")
    try:
        df = pd.read_csv(data_path)
    except FileNotFoundError:
        print(f"Error: Could not find {data_path}")
        return

    # Check for required columns
    if 'clause_text' not in df.columns or 'risk_level' not in df.columns:
        print("Error: Dataset must contain 'clause_text' and 'risk_level' columns.")
        return

    # Prepare features and target
    X = df['clause_text']
    y = df['risk_level']

    # Split into train and test sets (80/20)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Initialize TF-IDF Vectorizer with ngram_range=(1,2)
    print("Vectorizing text...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
    X_train_tfidf = vectorizer.fit_transform(X_train)
    X_test_tfidf = vectorizer.transform(X_test)

    # Initialize and train Random Forest Classifier
    print("Training Random Forest Classifier...")
    classifier = RandomForestClassifier(n_estimators=100, random_state=42)
    classifier.fit(X_train_tfidf, y_train)

    # Make predictions and print Classification Report
    print("Evaluating model...")
    y_pred = classifier.predict(X_test_tfidf)
    print("\n--- Classification Report ---")
    print(classification_report(y_test, y_pred))

    # Save the model and vectorizer
    joblib.dump(classifier, model_path)
    joblib.dump(vectorizer, vectorizer_path)
    
    print(f"Model saved to {model_path}")
    print(f"Vectorizer saved to {vectorizer_path}")

if __name__ == "__main__":
    main()
