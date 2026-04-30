# data_processor.py - Processing user input for NeuroCure+
import re

class NeuroDataProcessor:
    def __init__(self):
        # Common unimportant words (Stopwords)
        self.stopwords = ["i", "am", "feeling", "a", "the", "is", "have", "suffering", "from", "and", "with", "since"]
        
        # Medical Keywords Mapping (Basic NLP)
        self.symptom_map = {
            "temperature": "fever",
            "burning": "fever",
            "head": "headache",
            "migraine": "headache",
            "throat": "cough",
            "sneezing": "cold"
        }

    def clean_text(self, text):
        """User input text ke clean kore lowecase ebong special characters remove kore"""
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text) # Remove punctuation
        return text

    def extract_keywords(self, text):
        """Text theke main medical keywords ber kore"""
        cleaned_text = self.clean_text(text)
        words = cleaned_text.split()
        
        # Stopwords bad deya
        filtered_words = [w for w in words if w not in self.stopwords]
        
        # Logic to map related words to main symptoms
        found_keywords = []
        for word in filtered_words:z
            if word in self.symptom_map:
                found_keywords.append(self.symptom_map[word])
            else:
                found_keywords.append(word)
                
        return list(set(found_keywords)) # Duplicate remove kora

# Testing the processor (Demo purpose)
if __name__ == "__main__":
    processor = NeuroDataProcessor()
    sample_input = "I am feeling a heavy headache and a bit of temperature!"
    keywords = processor.extract_keywords(sample_input)
    print(f"Original: {sample_input}")
    print(f"Processed Keywords: {keywords}")