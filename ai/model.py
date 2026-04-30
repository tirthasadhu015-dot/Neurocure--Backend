# model.py - AI Matching Logic for NeuroCure+
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class NeuroCureModel:
    def __init__(self, csv_path='medicine_data.csv'):
        # Data load kora
        self.df = pd.read_csv(csv_path)
        self.vectorizer = TfidfVectorizer()
        
        # Medicine data-r symptoms gulo ke AI model-e train kora
        self.symptom_vectors = self.vectorizer.fit_transform(self.df['Symptom'])

    def predict(self, user_input):
        # User input ke vector-e convert kora
        user_vector = self.vectorizer.transform([user_input])
        
        # Similarity check kora (User input-er sathe dataset-er mil koto)
        similarities = cosine_similarity(user_vector, self.symptom_vectors)
        
        # Shobcheye beshi matching row-ta khuje ber kora
        index = similarities.argmax()
        score = similarities[0][index]

        # Jodi mil 0.3 (30%) er niche hoy, tobe amra bolbo 'match paini'
        if score < 0.3:
            return {
                "reply": "I'm not exactly sure. Could you please provide more details about your symptoms?",
                "confidence": float(score)
            }

        # Match paoa gele database theke info neya
        row = self.df.iloc[index]
        return {
            "symptom": row['Symptom'],
            "medicine": row['Medicine'],
            "dosage": row['Dosage'],
            "precaution": row['Precaution'],
            "severity": row['Severity'],
            "confidence": float(score),
            "reply": f"Based on your symptoms, you might have {row['Symptom']}. Suggested medicine is {row['Medicine']} ({row['Dosage']}). Precaution: {row['Precaution']}."
        }

# Testing (Demo purpose)
if __name__ == "__main__":
    model = NeuroCureModel()
    result = model.predict("I have a very high body temperature and shivering")
    print(f"AI Prediction: {result['reply']}")
    print(f"Confidence Score: {result['confidence']}")
    # model.py logic ensure koro
def predict(self, user_input):
    user_input = user_input.lower()
    # CSV theke protiti row check korbe
    for index, row in self.df.iterrows():
        if row['Symptom'].lower() in user_input:
            return {
                "reply": f"It looks like {row['Symptom']}. Recommended: {row['Medicine']}. Dosage: {row['Dosage']}.",
                "status": "success"
            }
    return {"reply": "Sorry, I don't have information on this disease yet."}