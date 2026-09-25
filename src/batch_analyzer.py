import csv
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

from serper_search import SerperClient
from intent_detector import IntentDetector
from classifier import ResultClassifier
from content_strategy_analyzer import ContentStrategyAnalyzer
from output_writer import OutputWriter

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_query(query: str, num_results: int = 10):
    """Analyze a single query and return the analysis"""
    try:
        logger.info(f"Analyzing: {query}")
        
        # Fetch results
        search_client = SerperClient()
        results = search_client.search(query, num_results=num_results)
        
        if not results:
            logger.warning(f"No results found for: {query}")
            return None
        
        timestamp = datetime.now().isoformat(timespec="seconds")
        
        analysis = {
            'query': query,
            'timestamp': timestamp,
            'total_results': len(results),
            'results': results
        }
        
        # Detect intent
        intent_detector = IntentDetector()
        analysis['intent'] = intent_detector.detect_intent(query, results)
        
        # Classify results
        classifier = ResultClassifier()
        for result in analysis['results']:
            result['classification'] = classifier.classify_result(result)
        
        classification_summary = {}
        for result in analysis['results']:
            category = result.get('classification', {}).get('category', 'unknown')
            classification_summary[category] = classification_summary.get(category, 0) + 1
        analysis['classification_summary'] = classification_summary
        
        # Generate strategy
        strategy_analyzer = ContentStrategyAnalyzer()
        analysis['content_strategy'] = strategy_analyzer.analyze(
            query=query,
            results=analysis['results'],
            user_intent=analysis.get('intent')
        )
        
        logger.info(f"✓ Completed: {query}")
        return analysis
        
    except Exception as e:
        logger.error(f"✗ Failed analyzing '{query}': {e}")
        return None


def batch_analyze(input_file: str, output_dir: str = "./outputs", delay: int = 2):
    """Analyze multiple queries from a CSV file"""
    input_path = Path(input_file)
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_file}")
        return
    
    # Read queries
    queries = []
    with open(input_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'query' not in reader.fieldnames:
            logger.error("CSV must have a 'query' column")
            return
        
        for row in reader:
            query = row['query'].strip()
            if query:
                queries.append(query)
    
    if not queries:
        logger.error("No queries found")
        return
    
    logger.info(f"Found {len(queries)} queries")
    
    # Create batch directory
    batch_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = Path(output_dir) / f"batch_{batch_timestamp}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    writer = OutputWriter(base_dir=str(batch_dir))
    results = []
    
    for i, query in enumerate(queries, 1):
        logger.info(f"\n[{i}/{len(queries)}] Processing: {query}")
        
        analysis = analyze_query(query)
        if analysis:
            results.append(analysis)
            
            # Save individual files
            safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
            safe_query = safe_query.replace(' ', '_')
            writer.write_all_formats(analysis, base_filename=f"{i:02d}_{safe_query}")
        
        if i < len(queries):
            time.sleep(delay)
    
    # Create combined summary
    if results:
        logger.info("\nCreating combined summary...")
        combined_csv = batch_dir / "00_COMBINED_ANALYSIS.csv"
        
        fieldnames = [
            'query', 'user_intent', 'intent_confidence',
            'commercial_pct', 'informational_pct', 
            'recommended_content_type', 'recommended_format', 
            'recommended_angle', 'strategy_confidence', 'required_elements'
        ]
        
        with open(combined_csv, 'w', newline='', encoding='utf-8') as f:
            writer_csv = csv.DictWriter(f, fieldnames=fieldnames)
            writer_csv.writeheader()
            
            for analysis in results:
                dist = analysis['content_strategy']['result_distribution']['percentages']
                rec = analysis['content_strategy']['recommendation']
                
                row = {
                    'query': analysis['query'],
                    'user_intent': analysis['intent']['user_intent'],
                    'intent_confidence': analysis['intent']['confidence'],
                    'commercial_pct': dist.get('commercial', 0),
                    'informational_pct': dist.get('informational', 0),
                    'recommended_content_type': rec['content_type'],
                    'recommended_format': rec['format'],
                    'recommended_angle': rec['angle'],
                    'strategy_confidence': rec['confidence'],
                    'required_elements': '; '.join(rec.get('required_elements', []))
                }
                writer_csv.writerow(row)
        
        logger.info(f"\n✓ Complete! Output: {batch_dir}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python batch_analyzer.py queries.csv")
        sys.exit(1)
    
    batch_analyze(sys.argv[1])