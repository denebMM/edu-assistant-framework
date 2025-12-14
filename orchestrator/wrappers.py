import time
import ollama
import spacy
import requests
import os
from typing import Tuple
# ← CORREGIDO: make_classification viene de sklearn.datasets
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier


class RuleBasedWrapper:
    def __init__(self):
        self.api_url = f"{os.getenv('RULE_BASED_HOST', 'http://rule-based:5001')}/query"

    def process(self, query):
        start = time.time()
        payload = {"query": query}
        try:
            r = requests.post(self.api_url, json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
           # ACEPTA AMBOS FORMATOS
            if "output_data" in data and "response" in data["output_data"]:
                output = data["output_data"]["response"]
            elif "response" in data:
                output = data["response"]
            else:
                output = "Rule-based devolvió formato inesperado"
            error_rate = 0.0
        except Exception as e:
            output = f"[Rule-based error]: {e}"
            error_rate = 1.0
        latency = time.time() - start
        return output, latency, error_rate


class DeepPavlovWrapper:
    def __init__(self):
        self.api_url = f"{os.getenv('DEEPPAVLOV_HOST', 'http://deeppavlov-nlu:5002')}/query"

    def process(self, query: str) -> Tuple[str, float, float]:
        start = time.time()
        payload = {"query": query}
        try:
            r = requests.post(self.api_url, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            # TU WRAPPER DEVUELVE {"response": "..."} → ¡ACEPTAMOS ESO!
            output = data.get("response", "DeepPavlov no devolvió respuesta")
            error_rate = 0.0
        except Exception as e:
            output = f"[DeepPavlov error]: {e}"
            error_rate = 1.0
        latency = time.time() - start
        return output, latency, error_rate

class LLMWrapper:
    def __init__(self):
        self.model = 'tinyllama'

    def process(self, query):
        start = time.time()
        try:
            resp = ollama.chat(model=self.model, messages=[{'role': 'user', 'content': query}])
            output = resp['message']['content']
            error_rate = 0.0
        except Exception as e:
            output = f"[Ollama error]: {e}"
            error_rate = 1.0
        latency = time.time() - start
        return output, latency, error_rate


class NLUWrapper:
    def __init__(self):
        self.nlp = spacy.load('en_core_web_sm')

    def process(self, query):
        start = time.time()
        doc = self.nlp(query)
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        latency = time.time() - start
        return f"Entidades detectadas: {entities}", latency, 0.0


class MLWrapper:
    def __init__(self):
        X, y = make_classification(n_samples=100, random_state=42)
        self.model = RandomForestClassifier()
        self.model.fit(X, y)

    def process(self, query):
        start = time.time()
        pred = self.model.predict([[len(query)] * 20])[0]
        latency = time.time() - start
        return f"Recomendación educativa (ML): nivel {pred}", latency, 0.0