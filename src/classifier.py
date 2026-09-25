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
        
        prompt = f"""Classify the following search result in two ways.

1. category (the purpose of the page), one of:
- informational: Educational content, how-to guides, explanations, forum discussions
- commercial: Product pages, service offerings, business sites
- navigational: Brand pages, login pages, specific site navigation
- transactional: E-commerce, booking, download pages
- local: Local businesses, maps, location-specific results
- news: News articles, current events, press releases (forum threads are never news)

2. page_type (the format of the page), one of:
- how_to_guide: step-by-step instructions or a practical guide
- explainer: explains what something is and how it works
- listicle: numbered list of items, tips or options
- comparison: compares specific options side by side
- review: evaluates one or more products or services
- service_page: a business selling a service
- product_page: a single product for sale
- category_page: a store or directory page listing many products or providers
- tool: an interactive tool, calculator or generator
- video: a video page such as YouTube
- forum_thread: Reddit, Quora, community or Q&A discussion
- news_article: a news story or press release
- research_paper: academic paper, journal article or formal report
- program_page: a course, certification, training or membership page
- other: none of the above

Search Result:
Title: {title}
URL: {url}
Snippet: {snippet}

Respond with a JSON object containing:
- category: one of the categories above
- page_type: one of the page types above
- confidence: a number between 0 and 1
- reasoning: brief explanation (1-2 sentences)

Example response:
{{"category": "informational", "page_type": "how_to_guide", "confidence": 0.92, "reasoning": "This is a how-to guide explaining a process."}}"""
        
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
            # Strip ```json fences in case the model adds them
            result_text = result_text.replace("```json", "").replace("```", "").strip()
            
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
    
    def filter_questions(self, query: str, questions: list, titles: list) -> Dict[str, list]:
        """
        Split People Also Ask questions into on-topic and off-topic.
        The top result titles tell the model which meaning of the search Google is showing,
        so questions about a different meaning (for example tax audits for "ai audit") get removed.
        Returns {"keep": [...], "removed": [...]}. On any error, keeps everything.
        """
        if not questions:
            return {"keep": [], "removed": []}

        numbered = "\n".join(f"{i}. {q}" for i, q in enumerate(questions))
        title_list = "\n".join(f"- {t}" for t in titles[:10])
        prompt = f"""A writer is planning an article for the search "{query}".

These are the titles of the top Google results, which show what the search means:
{title_list}

These are Google's "People Also Ask" questions:
{numbered}

Which questions are about the same topic as the top results and would belong in the writer's article?
Remove questions about a different meaning of the words or an unrelated topic.

Respond with JSON only: {{"keep": [question numbers to keep]}}"""

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You filter search questions for relevance. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=100
            )
            text = response.choices[0].message.content.strip()
            text = text.replace("```json", "").replace("```", "").strip()
            keep_idx = {int(i) for i in json.loads(text).get("keep", [])}
            return {
                "keep": [q for i, q in enumerate(questions) if i in keep_idx],
                "removed": [q for i, q in enumerate(questions) if i not in keep_idx],
            }
        except Exception as e:
            logger.error(f"Question filtering failed, keeping all questions: {e}")
            return {"keep": list(questions), "removed": []}

    def batch_classify(self, results: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        classified_results = []
        
        for result in results:
            classification = self.classify_result(result)
            result_with_classification = result.copy()
            result_with_classification['classification'] = classification
            classified_results.append(result_with_classification)
        
        return classified_results