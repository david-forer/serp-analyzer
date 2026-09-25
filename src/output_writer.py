import json
import csv
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any


class OutputWriter:
    def __init__(self, base_dir: str = "./outputs"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def write_json(self, data: Dict[str, Any], filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"serp_analysis_{timestamp}.json"
        
        filepath = self.base_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def write_csv(self, results: List[Dict[str, Any]], filename: str = None, 
                  query_intent: Dict[str, Any] = None,
                  content_strategy: Dict[str, Any] = None) -> str:
        """
        Write results to CSV with query-level intent and strategy data included in each row.
        
        Args:
            results: List of search results with their classifications
            filename: Optional output filename
            query_intent: Query-level intent data to be added to each row
            content_strategy: Content strategy recommendation to be added to each row
        """
        if not results:
            return None
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"serp_analysis_{timestamp}.csv"
        
        filepath = self.base_dir / filename
        
        # Extended fieldnames with content strategy
        fieldnames = [
            'position', 'title', 'url', 'snippet', 
            'user_intent', 'intent_confidence', 
            'result_type', 'page_type', 'result_confidence',
            # Content strategy columns (query-level)
            'verdict', 'recommended_content_type', 'recommended_format', 'recommended_angle',
            'strategy_confidence', 'required_elements'
        ]
        
        # Extract strategy recommendation
        strategy_rec = content_strategy.get('recommendation', {}) if content_strategy else {}
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results:
                # Combine required elements into a semicolon-separated string
                elements = strategy_rec.get('required_elements', [])
                elements_str = '; '.join(elements) if elements else ''
                
                row = {
                    'position': result.get('position', ''),
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'snippet': result.get('snippet', ''),
                    # Query-level intent (same for all rows)
                    'user_intent': query_intent.get('user_intent', '') if query_intent else '',
                    'intent_confidence': query_intent.get('confidence', '') if query_intent else '',
                    # Result-level classification (varies per row)
                    'result_type': result.get('classification', {}).get('category', ''),
                    'page_type': result.get('classification', {}).get('page_type', ''),
                    'result_confidence': result.get('classification', {}).get('confidence', ''),
                    # Content strategy (same for all rows)
                    'verdict': strategy_rec.get('verdict', {}).get('summary', ''),
                    'recommended_content_type': strategy_rec.get('content_type', ''),
                    'recommended_format': strategy_rec.get('format', ''),
                    'recommended_angle': strategy_rec.get('angle', ''),
                    'strategy_confidence': strategy_rec.get('confidence', ''),
                    'required_elements': elements_str
                }
                writer.writerow(row)
        
        return str(filepath)
    
    def write_summary(self, analysis: Dict[str, Any], filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"serp_analysis_{timestamp}_summary.txt"
        
        filepath = self.base_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SERP ANALYSIS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Query: {analysis.get('query', 'N/A')}\n")
            f.write(f"Timestamp: {analysis.get('timestamp', 'N/A')}\n")
            f.write(f"Total Results: {analysis.get('total_results', 0)}\n\n")
            
            # USER INTENT SECTION
            if 'intent' in analysis:
                f.write("=" * 80 + "\n")
                f.write("USER INTENT\n")
                f.write("=" * 80 + "\n")
                intent = analysis['intent']
                f.write(f"What the user wants:\n  {intent.get('user_intent', 'N/A')}\n\n")
                f.write(f"Confidence: {intent.get('confidence', 'N/A')}\n")
                
                if intent.get('key_signals'):
                    f.write(f"Key Signals: {', '.join(intent.get('key_signals', []))}\n")
                
                f.write(f"\nReasoning: {intent.get('reasoning', 'N/A')}\n\n")
            
            # RESULT ANALYSIS SECTION
            if 'classification_summary' in analysis:
                f.write("=" * 80 + "\n")
                f.write("RESULT TYPE DISTRIBUTION\n")
                f.write("=" * 80 + "\n")
                summary = analysis['classification_summary']
                total = sum(summary.values())
                for category, count in sorted(summary.items(), key=lambda x: x[1], reverse=True):
                    pct = (count / total * 100) if total > 0 else 0
                    bar = "█" * int(pct / 5)  # Visual bar
                    f.write(f"{category:20s} {count:2d} ({pct:5.1f}%) {bar}\n")
                f.write("\n")
            
            # CONTENT STRATEGY SECTION (NEW!)
            if 'content_strategy' in analysis:
                strategy = analysis['content_strategy']
                rec = strategy.get('recommendation', {})
                
                f.write("=" * 80 + "\n")
                f.write("CONTENT STRATEGY RECOMMENDATION\n")
                f.write("=" * 80 + "\n\n")
                
                if rec.get('verdict'):
                    f.write(f"VERDICT:\n  {rec['verdict']['summary']}\n\n")
                
                f.write(f"CONTENT TYPE:\n  {rec.get('content_type', 'N/A')}\n\n")
                f.write(f"FORMAT:\n  {rec.get('format', 'N/A')}\n\n")
                f.write(f"ANGLE:\n  {rec.get('angle', 'N/A')}\n\n")
                
                f.write("REQUIRED ELEMENTS:\n")
                for element in rec.get('required_elements', []):
                    f.write(f"  • {element}\n")
                f.write("\n")
                
                f.write(f"CONFIDENCE: {rec.get('confidence', 0):.0%}\n\n")
                
                f.write("WHY THIS APPROACH:\n")
                for reason in rec.get('reasoning', []):
                    f.write(f"  • {reason}\n")
                f.write("\n")
                
                # Additional insights
                f.write("-" * 80 + "\n")
                f.write("DETAILED ANALYSIS\n")
                f.write("-" * 80 + "\n\n")
                
                # Title patterns
                if 'title_patterns' in strategy:
                    patterns = strategy['title_patterns']
                    f.write("Title Patterns:\n")
                    if patterns.get('is_listicle', 0) >= 3:
                        f.write(f"  • {patterns['is_listicle']}/10 results use listicle format\n")
                    if patterns.get('has_year', 0) >= 3:
                        f.write(f"  • {patterns['has_year']}/10 include current year (freshness matters)\n")
                    if patterns.get('has_comparison', 0) >= 3:
                        f.write(f"  • {patterns['has_comparison']}/10 include comparison keywords\n")
                    if patterns.get('has_best_top', 0) >= 5:
                        f.write(f"  • {patterns['has_best_top']}/10 use 'best' or 'top' in title\n")
                    f.write("\n")
                
                # Content depth
                if 'depth_analysis' in strategy:
                    depth = strategy['depth_analysis']
                    f.write(f"Content Depth Level: {depth.get('depth_level', 'unknown').upper()}\n")
                    f.write("Key Elements Found in Ranking Content:\n")
                    for element in depth.get('key_elements', []):
                        score = depth['scores'].get(element, 0)
                        f.write(f"  • {element.replace('_', ' ').title()}: {score} indicators\n")
                    f.write("\n")
            
            # TOP RESULTS SECTION
            if 'results' in analysis:
                f.write("=" * 80 + "\n")
                f.write("TOP RANKING CONTENT\n")
                f.write("=" * 80 + "\n\n")
                for idx, result in enumerate(analysis['results'][:10], 1):
                    result_type = result.get('classification', {}).get('category', 'unknown')
                    f.write(f"#{idx} [{result_type.upper()}] {result.get('title', 'N/A')}\n")
                    f.write(f"    {result.get('url', 'N/A')}\n")
                    snippet = result.get('snippet', 'N/A')[:150]
                    f.write(f"    {snippet}...\n\n")
        
        return str(filepath)
    
    def write_all_formats(self, analysis: Dict[str, Any], base_filename: str = None) -> Dict[str, str]:
        if base_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = f"serp_analysis_{timestamp}"
        
        outputs = {}
        
        outputs['json'] = self.write_json(analysis, f"{base_filename}.json")
        
        if 'results' in analysis:
            # Pass both query-level intent AND content strategy to CSV writer
            query_intent = analysis.get('intent', None)
            content_strategy = analysis.get('content_strategy', None)
            outputs['csv'] = self.write_csv(
                analysis['results'], 
                f"{base_filename}.csv",
                query_intent=query_intent,
                content_strategy=content_strategy
            )
        
        outputs['summary'] = self.write_summary(analysis, f"{base_filename}_summary.txt")
        
        return outputs
