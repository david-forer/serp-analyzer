import argparse
import sys
from pathlib import Path
from typing import Optional
import logging

from serper_search import SerperClient
from datetime import datetime
from intent_detector import IntentDetector
from classifier import ResultClassifier
from content_strategy_analyzer import ContentStrategyAnalyzer
from output_writer import OutputWriter


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='SERP Analyzer - Analyze search results with intent detection and content strategy recommendations'
    )
    
    parser.add_argument(
        'query',
        type=str,
        help='Search query to analyze'
    )
    
    parser.add_argument(
        '-n', '--num-results',
        type=int,
        default=10,
        help='Number of results to fetch (default: 10)'
    )
    
    parser.add_argument(
        '-o', '--output-dir',
        type=str,
        default='./outputs',
        help='Output directory for results (default: ./outputs)'
    )
    
    parser.add_argument(
        '-f', '--format',
        choices=['json', 'csv', 'summary', 'all'],
        default='all',
        help='Output format (default: all)'
    )
    
    parser.add_argument(
        '--no-intent',
        action='store_true',
        help='Skip intent detection'
    )
    
    parser.add_argument(
        '--no-classify',
        action='store_true',
        help='Skip result classification'
    )
    
    parser.add_argument(
        '--no-strategy',
        action='store_true',
        help='Skip content strategy analysis'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        logger.info(f"Starting SERP analysis for query: '{args.query}'")
        
        search_client = SerperClient()
        logger.info("Fetching search results...")
        results = search_client.search(args.query, num_results=args.num_results)
        timestamp = datetime.now().isoformat(timespec="seconds")
        
        if not results:
            logger.error("No results found")
            sys.exit(1)
        
        logger.info(f"Found {len(results)} results")
        
        analysis = {
            'query': args.query,
            'timestamp': timestamp,
            'total_results': len(results),
            'results': results
        }
        
        # Step 1: Detect user intent
        if not args.no_intent:
            logger.info("Detecting search intent...")
            intent_detector = IntentDetector()
            intent_analysis = intent_detector.detect_intent(args.query, results)
            analysis['intent'] = intent_analysis
            logger.info(f"User intent: {intent_analysis.get('user_intent', 'N/A')[:100]}...")
        
        # Step 2: Classify each result
        if not args.no_classify:
            logger.info("Classifying results...")
            classifier = ResultClassifier()
            
            for result in analysis['results']:
                classification = classifier.classify_result(result)
                result['classification'] = classification
            
            classification_summary = {}
            for result in analysis['results']:
                category = result.get('classification', {}).get('category', 'unknown')
                classification_summary[category] = classification_summary.get(category, 0) + 1
            
            analysis['classification_summary'] = classification_summary
            logger.info(f"Classification summary: {classification_summary}")
        
        # Step 3: Generate content strategy recommendation
        if not args.no_strategy:
            logger.info("Analyzing content strategy...")
            strategy_analyzer = ContentStrategyAnalyzer()
            
            user_intent = analysis.get('intent', None)
            strategy_analysis = strategy_analyzer.analyze(
                query=args.query,
                results=analysis['results'],
                user_intent=user_intent
            )
            
            analysis['content_strategy'] = strategy_analysis
            logger.info(f"Recommended content type: {strategy_analysis['recommendation']['content_type']}")
        
        # Create organized folder structure
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_query = "".join(c for c in args.query if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        safe_query = safe_query.replace(' ', '_')
        
        # Create folder: outputs/20251004_210530_best_CMMS_software/
        analysis_folder = Path(args.output_dir) / f"{timestamp_str}_{safe_query}"
        analysis_folder.mkdir(parents=True, exist_ok=True)
        
        # Write outputs to the organized folder
        logger.info("Writing outputs...")
        writer = OutputWriter(base_dir=str(analysis_folder))
        
        output_files = {}
        
        # Use simple filenames since they're already in a dated folder
        base_filename = "analysis"
        
        if args.format == 'json':
            output_files['json'] = writer.write_json(analysis, filename=f"{base_filename}.json")
        elif args.format == 'csv':
            output_files['csv'] = writer.write_csv(
                analysis['results'],
                filename=f"{base_filename}.csv",
                query_intent=analysis.get('intent'),
                content_strategy=analysis.get('content_strategy')
            )
        elif args.format == 'summary':
            output_files['summary'] = writer.write_summary(analysis, filename=f"{base_filename}_summary.txt")
        else:
            output_files = writer.write_all_formats(analysis, base_filename=base_filename)
        
        logger.info("Analysis complete!")
        logger.info(f"Output folder: {analysis_folder}")
        logger.info("Files created:")
        for format_type, filepath in output_files.items():
            if filepath:
                logger.info(f"  - {Path(filepath).name}")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Error during analysis: {str(e)}", exc_info=args.verbose)
        return 1


if __name__ == '__main__':
    sys.exit(main())
