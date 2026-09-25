import openai
import os
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)


class ResultClassifier:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
        
        openai.api_key = self.api_key
    
    def classify_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        title = result.get('title', '')
        snippet = result.get('snippet', '')
        url = result.get('url', '')
        
        prompt = f"""Classify the following search result into one of these categories:
- informational: Educational content, how-to guides, explanations
- commercial: Product pages, service offerings, business sites
- navigational: Brand pages, login pages, specific site navigation
- transactional: E-commerce, booking, download pages
- local: Local businesses, maps, location-specific results
- news: News articles, current events, press releases

Search Result:
Title: {title}
URL: {url}
Snippet: {snippet}

Respond with a JSON object containing:
- category: one of the categories above
- confidence: a number between 0 and 1
- reasoning: brief explanation (1-2 sentences)

Example response:
{{"category": "informational", "confidence": 0.92, "reasoning": "This is a how-to guide explaining a process."}}"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a search result classifier. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            result_text = response.choices[0].message.content.strip()
            
            classification = json.loads(result_text)
            
            return classification
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification response: {e}")
            return {
                "category": "unknown",
                "confidence": 0.0,
                "reasoning": "Failed to classify result"
            }
        except Exception as e:
            logger.error(f"Error classifying result: {e}")
            return {
                "category": "unknown",
                "confidence": 0.0,
                "reasoning": f"Error: {str(e)}"
            }
    
    def batch_classify(self, results: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        classified_results = []
        
        for result in results:
            classification = self.classify_result(result)
            result_with_classification = result.copy()
            result_with_classification['classification'] = classification
            classified_results.append(result_with_classification)
        
        return classified_results