# content_strategy_analyzer.py
import re
from typing import Dict, Any, List
from collections import Counter
import logging

logger = logging.getLogger(__name__)


class ContentStrategyAnalyzer:
    """
    Analyzes SERP results to determine what type of content to create.
    Looks at patterns in ranking content to recommend content strategy.
    """
    
    def __init__(self):
        # Common patterns that indicate content types
        self.listicle_patterns = [
            r'\b\d+\s+(?:best|top|ways|tips|tools|software|apps|ideas|examples)',
            r'\b(?:top|best)\s+\d+',
        ]
        
        self.comparison_keywords = [
            'vs', 'versus', 'compared', 'comparison', 'alternative',
            'difference'
        ]
        
        self.review_keywords = [
            'review', 'reviews', 'rated', 'ranking', 'ranked', 
            'evaluation', 'tested', 'rating'
        ]
        
        self.buying_guide_keywords = [
            'guide', 'how to choose', 'buying guide', 'what to look for',
            'considerations', 'factors', 'should you'
        ]
        
        self.depth_indicators = {
            'pricing': ['price', 'pricing', 'cost', 'free', '$', 'paid', 'subscription'],
            'features': ['features', 'functionality', 'capabilities', 'includes'],
            'comparison': ['compare', 'vs', 'versus', 'alternative', 'compared to'],
            'pros_cons': ['pros', 'cons', 'advantages', 'disadvantages', 'benefits', 'drawbacks'],
            'specs': ['specifications', 'specs', 'technical', 'requirements']
        }
    
    @staticmethod
    def _has_word(text: str, keyword: str) -> bool:
        """True if keyword appears as a whole word or phrase, not inside another word"""
        return re.search(r'\b' + re.escape(keyword) + r'\b', text) is not None

    def analyze(self, query: str, results: List[Dict[str, Any]], 
                user_intent: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main analysis method - returns content strategy recommendations
        """
        analysis = {
            'query': query,
            'total_results_analyzed': len(results)
        }
        
        # Analyze result type distribution
        analysis['result_distribution'] = self._analyze_result_distribution(results)
        
        # Analyze title patterns
        analysis['title_patterns'] = self._analyze_title_patterns(results)
        
        # Analyze content format signals
        analysis['format_signals'] = self._analyze_format_signals(results)
        
        # Analyze content depth indicators
        analysis['depth_analysis'] = self._analyze_content_depth(results)
        
        # Analyze domain patterns
        analysis['domain_patterns'] = self._analyze_domains(results)
        
        # Generate recommendation
        analysis['recommendation'] = self._generate_recommendation(
            analysis, user_intent, query
        )
        
        return analysis
    
    def _analyze_result_distribution(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the distribution of result types"""
        categories = []
        for result in results:
            cat = result.get('classification', {}).get('category', 'unknown')
            categories.append(cat)
        
        counts = Counter(categories)
        total = len(categories)
        
        distribution = {
            'counts': dict(counts),
            'percentages': {k: round(v/total * 100, 1) for k, v in counts.items()},
            'dominant_type': counts.most_common(1)[0][0] if counts else 'unknown',
            'diversity': len(counts)  # How many different types are ranking
        }
        
        return distribution
    
    def _analyze_title_patterns(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract patterns from result titles"""
        titles = [r.get('title', '') for r in results]
        all_titles_text = ' '.join(titles).lower()
        
        patterns = {
            'has_numbers': sum(1 for t in titles if re.search(r'\d+', t)),
            'is_listicle': sum(1 for t in titles if any(re.search(p, t.lower()) for p in self.listicle_patterns)),
            'has_year': sum(1 for t in titles if re.search(r'202[3-9]', t)),
            'has_comparison': sum(1 for t in titles if any(self._has_word(t.lower(), kw) for kw in self.comparison_keywords)),
            'has_review': sum(1 for t in titles if any(self._has_word(t.lower(), kw) for kw in self.review_keywords)),
            'has_guide': sum(1 for t in titles if any(self._has_word(t.lower(), kw) for kw in self.buying_guide_keywords)),
            'has_best_top': sum(1 for t in titles if re.search(r'\b(best|top)\b', t.lower())),
        }
        
        # Extract common words (excluding stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are'}
        words = re.findall(r'\b[a-z]{3,}\b', all_titles_text)
        word_freq = Counter(w for w in words if w not in stop_words)
        
        patterns['common_words'] = dict(word_freq.most_common(10))
        
        return patterns
    
    def _analyze_format_signals(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Determine what content formats are ranking"""
        all_text = []
        for r in results:
            all_text.append(r.get('title', '').lower())
            all_text.append(r.get('snippet', '').lower())
        
        combined_text = ' '.join(all_text)
        
        format_signals = {
            'listicle_score': sum(1 for p in self.listicle_patterns if re.search(p, combined_text)),
            'comparison_score': sum(1 for kw in self.comparison_keywords if self._has_word(combined_text, kw)),
            'review_score': sum(1 for kw in self.review_keywords if self._has_word(combined_text, kw)),
            'guide_score': sum(1 for kw in self.buying_guide_keywords if self._has_word(combined_text, kw)),
        }
        
        # Determine dominant format
        max_score = max(format_signals.values())
        if max_score == 0:
            dominant_format = 'general_content'
        else:
            dominant_format = max(format_signals.items(), key=lambda x: x[1])[0].replace('_score', '')
        
        format_signals['dominant_format'] = dominant_format
        
        return format_signals
    
    def _analyze_content_depth(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze how detailed the ranking content is"""
        all_snippets = ' '.join([r.get('snippet', '').lower() for r in results])
        
        depth_scores = {}
        for category, keywords in self.depth_indicators.items():
            score = sum(1 for kw in keywords if kw in all_snippets)
            depth_scores[category] = score
        
        total_depth = sum(depth_scores.values())
        depth_level = 'basic' if total_depth < 5 else 'moderate' if total_depth < 15 else 'comprehensive'
        
        return {
            'scores': depth_scores,
            'total_indicators': total_depth,
            'depth_level': depth_level,
            'key_elements': [k for k, v in depth_scores.items() if v > 0]
        }
    
    def _analyze_domains(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze what types of domains are ranking"""
        domains = []
        for r in results:
            url = r.get('url', '')
            if url:
                # Extract domain
                match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if match:
                    domain = match.group(1)
                    domains.append(domain)
        
        # Categorize domains
        vendor_patterns = ['product name', '.com', '.io', '.co']
        review_patterns = ['review', 'compare', 'best', 'top']
        community_patterns = ['reddit', 'forum', 'community', 'quora', 'stackexchange']
        
        domain_types = {
            'vendor_pages': 0,
            'review_sites': 0,
            'community': 0,
            'other': 0
        }
        
        for domain in domains:
            if any(p in domain for p in community_patterns):
                domain_types['community'] += 1
            elif any(p in domain for p in review_patterns):
                domain_types['review_sites'] += 1
            else:
                # Simple heuristic: if domain matches a product/service pattern
                domain_types['vendor_pages'] += 1
        
        unique_domains = len(set(domains))
        
        return {
            'unique_domains': unique_domains,
            'domain_diversity': 'high' if unique_domains >= 9 else 'moderate' if unique_domains >= 7 else 'low',
            'domain_types': domain_types
        }
    
    def _generate_recommendation(self, analysis: Dict[str, Any], 
                                 user_intent: Dict[str, Any], 
                                 query: str) -> Dict[str, Any]:
        """Generate specific content strategy recommendation"""
        dist = analysis['result_distribution']
        title_patterns = analysis['title_patterns']
        format_signals = analysis['format_signals']
        depth = analysis['depth_analysis']
        
        # Determine recommended content type
        content_type = self._determine_content_type(dist, format_signals, title_patterns)
        
        # Determine format
        format_rec = self._determine_format(format_signals, title_patterns)
        
        # Determine angle/approach
        angle = self._determine_angle(dist, depth, user_intent)
        
        # Determine required elements
        required_elements = self._determine_required_elements(depth, dist)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(analysis, content_type, format_rec)
        
        return {
            'content_type': content_type,
            'format': format_rec,
            'angle': angle,
            'required_elements': required_elements,
            'reasoning': reasoning,
            'confidence': self._calculate_confidence(analysis)
        }
    
    def _determine_content_type(self, dist: Dict, format_signals: Dict, 
                                title_patterns: Dict) -> str:
        """Determine what type of content to create"""
        dominant = format_signals.get('dominant_format', '')
        commercial_pct = dist['percentages'].get('commercial', 0)
        
        if 'listicle' in dominant or title_patterns['is_listicle'] >= 5:
            return 'Comparison Listicle (Top N Format)'
        elif 'comparison' in dominant or title_patterns['has_comparison'] >= 4:
            return 'Detailed Comparison Article'
        elif 'review' in dominant:
            return 'Multi-Product Review'
        elif 'guide' in dominant or title_patterns['has_guide'] >= 3:
            return 'Buying Guide / How to Choose'
        elif commercial_pct >= 60:
            return 'Product/Service Comparison & Review'
        else:
            return 'Informational Guide with Product Mentions'
    
    def _determine_format(self, format_signals: Dict, title_patterns: Dict) -> str:
        """Determine the specific format recommendation"""
        if title_patterns['is_listicle'] >= 5:
            # Find common number
            numbers = []
            for word in title_patterns.get('common_words', {}):
                if word.isdigit():
                    numbers.append(int(word))
            
            if numbers:
                avg_num = sum(numbers) // len(numbers)
                return f'Top {avg_num}-{avg_num+5} Listicle'
            return 'Top 10-15 Listicle'
        elif format_signals['comparison_score'] > format_signals['review_score']:
            return 'Head-to-Head Comparison Format'
        elif format_signals['guide_score'] >= 3:
            return 'Comprehensive Buying Guide'
        else:
            return 'Structured Review Article'
    
    def _determine_angle(self, dist: Dict, depth: Dict, 
                        user_intent: Dict[str, Any]) -> str:
        """Determine the content angle/approach"""
        commercial_pct = dist['percentages'].get('commercial', 0)
        has_pricing = depth['scores'].get('pricing', 0) > 2
        has_features = depth['scores'].get('features', 0) > 2
        
        if commercial_pct >= 60 and has_pricing:
            return 'Feature-by-feature comparison with pricing, use cases, and recommendations'
        elif commercial_pct >= 60:
            return 'Detailed vendor comparison with pros/cons and use case matching'
        elif has_features:
            return 'Educational approach with product examples and feature breakdowns'
        else:
            return 'Informational guide with curated product/service recommendations'
    
    def _determine_required_elements(self, depth: Dict, dist: Dict) -> List[str]:
        """Determine what elements must be included"""
        elements = []
        
        depth_scores = depth['scores']
        commercial_pct = dist['percentages'].get('commercial', 0)
        
        if depth_scores.get('pricing', 0) > 2:
            elements.append('Pricing information / cost comparison')
        
        if depth_scores.get('features', 0) > 2:
            elements.append('Detailed feature lists and capabilities')
        
        if depth_scores.get('pros_cons', 0) > 1:
            elements.append('Pros and cons for each option')
        
        if depth_scores.get('comparison', 0) > 2:
            elements.append('Direct comparison table/matrix')
        
        if commercial_pct >= 50:
            elements.append('Clear product/service recommendations')
        
        # Always include these basics
        elements.extend([
            'Use case scenarios / who each option is best for',
            'Clear verdict or recommendations section'
        ])
        
        return elements
    
    def _generate_reasoning(self, analysis: Dict, content_type: str, 
                          format_rec: str) -> List[str]:
        """Generate human-readable reasoning for the recommendation"""
        reasoning = []
        
        dist = analysis['result_distribution']
        title_patterns = analysis['title_patterns']
        depth = analysis['depth_analysis']
        
        # Reasoning based on result distribution
        dominant_type = dist['dominant_type']
        dominant_pct = dist['percentages'].get(dominant_type, 0)
        reasoning.append(
            f"{dominant_pct}% of results are {dominant_type} pages, "
            f"indicating users expect {self._get_expectation(dominant_type)}"
        )
        
        # Reasoning based on format
        if title_patterns['is_listicle'] >= 5:
            reasoning.append(
                f"{title_patterns['is_listicle']} out of 10 results use listicle format, "
                "showing strong preference for numbered comparisons"
            )
        
        if title_patterns['has_year'] >= 3:
            reasoning.append("Multiple results include current year, indicating freshness is important")
        
        # Reasoning based on depth
        if depth['depth_level'] == 'comprehensive':
            reasoning.append(
                f"Ranking content is highly detailed with {depth['total_indicators']} depth indicators, "
                "requiring comprehensive coverage"
            )
        
        return reasoning
    
    def _get_expectation(self, result_type: str) -> str:
        """Convert result type to user expectation"""
        expectations = {
            'commercial': 'vendor evaluation and purchase-ready information',
            'informational': 'educational content and explanations',
            'transactional': 'direct paths to purchase or signup',
            'navigational': 'specific brand or product information'
        }
        return expectations.get(result_type, 'varied content types')
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate confidence score for the recommendation"""
        # Higher confidence when:
        # - Clear dominant result type (>60%)
        # - Consistent title patterns (>50% match)
        # - Clear format signals
        
        dist = analysis['result_distribution']
        title_patterns = analysis['title_patterns']
        
        dominant_pct = max(dist['percentages'].values()) if dist['percentages'] else 0
        pattern_consistency = max(
            title_patterns['is_listicle'],
            title_patterns['has_comparison'],
            title_patterns['has_review']
        ) / 10  # Normalize to 0-1
        
        confidence = (dominant_pct / 100 * 0.6) + (pattern_consistency * 0.4)
        
        return round(min(confidence, 0.95), 2)  # Cap at 0.95
