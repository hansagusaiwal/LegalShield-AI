import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

def train():
    df = pd.read_csv('../data/legal_data.csv')
    X = df['text']
    y = df['risk_level']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    tfidf = TfidfVectorizer(max_features=1000)
    X_train_vec = tfidf.fit_transform(X_train)
    X_test_vec = tfidf.transform(X_test)

    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train_vec, y_train)

    y_pred = clf.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model training accuracy: {acc:.4f}")

    joblib.dump(clf, 'legal_risk_model.joblib')
    joblib.dump(tfidf, 'vectorizer.joblib')
    print("Model saved to legal_risk_model.joblib and vectorizer.joblib")

if __name__ == '__main__':
    train()
