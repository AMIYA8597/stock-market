import re

file_path = 'backend/app/services/sentiment_analyzer.py'
with open(file_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Replace initialize method
init_replacement = '''    def initialize(self) -> None:
        if self._initialized:
            return

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer

            logger.info("Initializing FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            self.model.eval()
            self._initialized = True
            logger.info("FinBERT model initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {e}")
            raise RuntimeError(f"Canonical sentiment analyzer FinBERT failed to load: {e}")'''

code = re.sub(r'    def initialize\(self\) -> None:.*?        self\.fast_mode = True', init_replacement, code, flags=re.DOTALL)

# Replace _vader_fallback
code = re.sub(r'    def _vader_fallback.*?        return \{"positive": scores\["pos"\], "negative": scores\["neg"\], "neutral": scores\["neu"\]\}', '', code, flags=re.DOTALL)

# Replace analyze_sentiment_batch
batch_replacement = '''    def analyze_sentiment_batch(self, texts: list[str]) -> list[dict[str, float]]:
        if not texts:
            return []

        if not self._initialized:
            self.initialize()

        try:
            import torch

            batch_size = 32
            results = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]
                inputs = self.tokenizer(
                    batch_texts, return_tensors="pt", truncation=True, padding=True, max_length=512
                )
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.softmax(outputs.logits, dim=-1).tolist()

                for p in probs:
                    results.append(
                        {
                            "positive": float(p[0]),
                            "negative": float(p[1]),
                            "neutral": float(p[2]),
                        }
                    )
            return results
        except Exception as e:
            logger.error(f"Sentiment inference failed: {e}")
            raise RuntimeError(f"Canonical sentiment inference failed: {e}")'''

code = re.sub(r'    def analyze_sentiment_batch\(self, texts: list\[str\]\) -> list\[dict\[str, float\]\]:.*?            return \[self\._vader_fallback\(t\) for t in texts\]', batch_replacement, code, flags=re.DOTALL)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(code)
print('Patched sentiment analyzer')
