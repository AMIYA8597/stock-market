import re

with open("app/services/llm_reasoning_engine.py", "r") as f:
    code = f.read()

validation_code = """
    @staticmethod
    def _validate_numeric_claims(text: str, evidence: dict) -> str:
        '''Enforces V2-25: LLM NEVER OWNS THE NUMBERS.'''
        import re
        
        # Extract all numbers from the text
        numbers = re.findall(r'-?\d+\.?\d*', text)
        
        # Extract all numbers from the evidence
        evidence_str = str(evidence)
        evidence_numbers = re.findall(r'-?\d+\.?\d*', evidence_str)
        
        # Check if any number in the text is NOT in the evidence
        for num_str in numbers:
            try:
                num = float(num_str)
                found = False
                for ev_num_str in evidence_numbers:
                    try:
                        if abs(num - float(ev_num_str)) < 0.001:
                            found = True
                            break
                    except:
                        pass
                
                # Allow common small integers like 14-day RSI
                if not found and num not in [0.0, 1.0, 14.0]:
                    logger.warning(f"LLM hallucinated number {num}. Stripping numerical claims.")
                    return LLMReasoningEngine._heuristic_fallback(evidence["signal"], evidence["technicals"], evidence["sentiment"])
            except:
                pass
                
        return text
"""

if "def _validate_numeric_claims" not in code:
    code = code.replace("    @staticmethod\n    def _heuristic_fallback", validation_code + "\n    @staticmethod\n    def _heuristic_fallback")
    
    # Modify generate_reasoning to call it
    call_replacement = """        try:
            raw_text = await provider.generate_text(prompt)
            evidence = {
                "signal": ensemble_signal,
                "confidence": confidence,
                "technicals": technicals,
                "sentiment": news_sentiment
            }
            return LLMReasoningEngine._validate_numeric_claims(raw_text, evidence)
        except Exception as e:"""
        
    code = re.sub(r'        try:\n            return await provider\.generate_text\(prompt\)\n        except Exception as e:', call_replacement, code)
    
    with open("app/services/llm_reasoning_engine.py", "w") as f:
        f.write(code)
