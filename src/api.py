import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add src to path for imports
src_dir = Path(__file__).parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from dataforseo_search import get_search_client
from intent_detector import IntentDetector
from classifier import ResultClassifier
from content_strategy_analyzer import ContentStrategyAnalyzer
from output_writer import OutputWriter

logger = logging.getLogger(__name__)


class Api:
    """API class exposed to the webview for SERP analysis."""

    def __init__(self):
        self._last_analysis = None

    def analyze(self, query: str, num_results: int = 10,
                detect_intent: bool = True,
                classify: bool = True,
                strategy: bool = True) -> dict:
        """
        Run SERP analysis on the given query.

        Args:
            query: Search query to analyze
            num_results: Number of results to fetch (5-20)
            detect_intent: Whether to run intent detection
            classify: Whether to classify results
            strategy: Whether to generate content strategy

        Returns:
            Analysis results dict
        """
        try:
            # Fetch search results
            search_client = get_search_client()
            results = search_client.search(query, num_results=num_results)

            if not results:
                return {"error": "No results found"}

            timestamp = datetime.now().isoformat(timespec="seconds")

            analysis = {
                "query": query,
                "timestamp": timestamp,
                "total_results": len(results),
                "results": results,
                "serp_features": search_client.last_features
            }

            # Step 1: Detect user intent
            if detect_intent:
                intent_detector = IntentDetector()
                intent_analysis = intent_detector.detect_intent(query, results)
                analysis["intent"] = intent_analysis

            # Step 2: Classify each result
            if classify:
                classifier = ResultClassifier()
                for result in analysis["results"]:
                    classification = classifier.classify_result(result)
                    result["classification"] = classification

                classification_summary = {}
                for result in analysis["results"]:
                    category = result.get("classification", {}).get("category", "unknown")
                    classification_summary[category] = classification_summary.get(category, 0) + 1

                analysis["classification_summary"] = classification_summary

                features = analysis.get("serp_features") or {}
                if features.get("people_also_ask"):
                    filtered = classifier.filter_questions(
                        query, features["people_also_ask"], [r.get("title", "") for r in results]
                    )
                    features["people_also_ask"] = filtered["keep"]
                    features["people_also_ask_removed"] = filtered["removed"]

            # Step 3: Generate content strategy recommendation
            if strategy:
                strategy_analyzer = ContentStrategyAnalyzer()
                user_intent = analysis.get("intent", None)
                strategy_analysis = strategy_analyzer.analyze(
                    query=query,
                    results=analysis["results"],
                    user_intent=user_intent,
                    serp_features=analysis.get("serp_features")
                )
                analysis["content_strategy"] = strategy_analysis

            self._last_analysis = analysis
            return analysis

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return {"error": str(e)}

    def export_json(self, output_dir: str = None) -> dict:
        """Export the last analysis to JSON."""
        if not self._last_analysis:
            return {"error": "No analysis to export. Run an analysis first."}

        try:
            if output_dir is None:
                output_dir = self._get_output_dir()

            writer = OutputWriter(base_dir=output_dir)
            filepath = writer.write_json(self._last_analysis, "analysis.json")
            return {"success": True, "path": filepath}
        except Exception as e:
            return {"error": str(e)}

    def export_csv(self, output_dir: str = None) -> dict:
        """Export the last analysis to CSV."""
        if not self._last_analysis:
            return {"error": "No analysis to export. Run an analysis first."}

        try:
            if output_dir is None:
                output_dir = self._get_output_dir()

            writer = OutputWriter(base_dir=output_dir)
            filepath = writer.write_csv(
                self._last_analysis.get("results", []),
                filename="analysis.csv",
                query_intent=self._last_analysis.get("intent"),
                content_strategy=self._last_analysis.get("content_strategy")
            )
            return {"success": True, "path": filepath}
        except Exception as e:
            return {"error": str(e)}

    def export_all(self, output_dir: str = None) -> dict:
        """Export the last analysis to all formats."""
        if not self._last_analysis:
            return {"error": "No analysis to export. Run an analysis first."}

        try:
            if output_dir is None:
                output_dir = self._get_output_dir()

            writer = OutputWriter(base_dir=output_dir)
            outputs = writer.write_all_formats(self._last_analysis, "analysis")
            return {"success": True, "paths": outputs}
        except Exception as e:
            return {"error": str(e)}

    def _get_output_dir(self) -> str:
        """Generate output directory path based on query and timestamp."""
        if not self._last_analysis:
            return "./outputs"

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        query = self._last_analysis.get("query", "analysis")
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        safe_query = safe_query.replace(' ', '_')

        # Get project root
        project_root = Path(__file__).parent.parent
        output_dir = project_root / "outputs" / f"{timestamp_str}_{safe_query}"
        output_dir.mkdir(parents=True, exist_ok=True)

        return str(output_dir)

    def get_last_analysis(self) -> dict:
        """Return the last analysis results."""
        if self._last_analysis:
            return self._last_analysis
        return {"error": "No analysis available"}
