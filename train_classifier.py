"""
Trains a lightweight intent classifier that routes a question to
"doc", "image", or "both" — using the same SentenceTransformer
embeddings already used elsewhere in the project, plus scikit-learn.
"""

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from backend.embeddings import model  # reuse the existing SentenceTransformer
from training_data import TRAINING_DATA


def main():
    questions = [q for q, _ in TRAINING_DATA]
    labels = [label for _, label in TRAINING_DATA]

    print(f"Training on {len(questions)} examples...")
    print("Encoding questions into embeddings...")
    embeddings = model.encode(questions)

    X_train, X_test, y_train, y_test = train_test_split(
        embeddings, labels, test_size=0.2, random_state=42, stratify=labels
    )

    print("Training classifier...")
    classifier = LogisticRegression(max_iter=1000)
    classifier.fit(X_train, y_train)

    print("\nEvaluation on held-out test set:")
    predictions = classifier.predict(X_test)
    print(classification_report(y_test, predictions))

    joblib.dump(classifier, "models/intent_classifier.pkl")
    print("\nSaved trained model to models/intent_classifier.pkl")


if __name__ == "__main__":
    main()