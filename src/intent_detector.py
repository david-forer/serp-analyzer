# intent_detector.py
import os
import json
import re
import logging
from typing import Dict, Any, List

import openai

logger = logging.getLogger(__name__)

def _parse_json_safe(text: str) -> Dict[str, Any]:
    """
    Parse model output robustly:
    - accept raw JSON
    - accept code-fenced JSON
    - extract the first {...} block if there's extra chatter
    - on failure, return a default structure
    """
    # 1) try direct
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2) strip Markdown fences
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    # 3) grab the first {} block
    braces = re.search(r"\{.*\}", text, re.S)
    if braces:
        try:
            return json.loads(braces.group(0))
        except Exception:
            pass

    # 4) last resort
    return {
        "user_intent": "Unable to determine user intent",
        "intent_type": "unknown",
        "confidence": 0.0,
        "key_signals": [],
        "reasoning": "Failed to parse JSON from model response."
    }

class IntentDetector:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        openai.api_key = self.api_key

    def detect_intent(self, query: str, results: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect the actual user intent - what they're trying to accomplish.
        Returns a detailed analysis of what the user wants to do, not just a category.
        """
        # Build concise context
        lines = [f"Search Query: {query}", ""]
        if results:
            lines.append("Top 5 Search Results:")
            for idx, r in enumerate(results[:5], 1):
                title = (r.get("title") or "N/A").strip()
                snippet = (r.get("snippet") or "N/A").replace("\n", " ")
                snippet = snippet[:220]
                lines.append(f"{idx}. {title}")
                lines.append(f"   Snippet: {snippet}")
                lines.append("")
        context = "\n".join(lines)

        system_prompt = (
            "You are a search intent analyzer. Analyze what the user is actually trying to accomplish. "
            "Return ONLY a valid JSON object with this schema:\n"
            "{\n"
            "  \"user_intent\": string (describe what the user wants to accomplish in 1-2 sentences),\n"
            "  \"intent_type\": string (informational/navigational/transactional/commercial),\n"
            "  \"confidence\": number (0-1),\n"
            "  \"key_signals\": array of strings (words/patterns that reveal intent),\n"
            "  \"reasoning\": string (brief explanation of the analysis)\n"
            "}\n"
        )

        user_prompt = f"""{context}

What is the user actually trying to accomplish with this search?
Describe their real goal and what action they want to take.
Respond ONLY with a JSON object."""

        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            raw = resp["choices"][0]["message"]["content"].strip()
            data = _parse_json_safe(raw)

            # Validate and normalize
            allowed_types = {"informational", "navigational", "transactional", "commercial"}
            intent_type = (data.get("intent_type") or "unknown").lower()
            if intent_type not in allowed_types:
                intent_type = "unknown"
            
            conf = data.get("confidence")
            try:
                conf = float(conf)
            except Exception:
                conf = 0.0
            
            signals = data.get("key_signals") or []
            if not isinstance(signals, list):
                signals = []

            clean = {
                "user_intent": str(data.get("user_intent") or "Unable to determine intent").strip()[:500] or "No intent provided",
                "intent_type": intent_type,
                "confidence": max(0.0, min(1.0, conf)),
                "key_signals": [str(s) for s in signals][:10],
                "reasoning": str(data.get("reasoning") or "").strip()[:600] or "No reasoning provided."
            }
            return clean

        except Exception as e:
            logger.error(f"Error detecting intent: {e}")
            return {
                "user_intent": f"Error analyzing intent: {str(e)}",
                "intent_type": "unknown",
                "confidence": 0.0,
                "key_signals": [],
                "reasoning": f"Error: {e}"
            }
