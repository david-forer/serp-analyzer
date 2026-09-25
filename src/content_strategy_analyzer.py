# content_strategy_analyzer.py
import re
from typing import Dict, Any, List
from collections import Counter
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


# What a writer should build when a given page type leads the SERP.
# "as_second" is used when the type is the runner-up and gets blended in.
# "warning" flags SERPs where an article is unlikely to rank.
PAGE_TYPE_PROFILES = {
    'how_to_guide': {
        'label': 'How-to guide', 'plural': 'how-to guides',
        'format': 'Step-by-step guide',
        'angle': 'Walk the reader through doing it themselves, in order.',
        'as_second': 'Include practical steps the reader can follow, since how-to guides rank here too.',
        'elements': ['Numbered steps the reader can follow',
                     'What the reader needs before starting',
                     'Common mistakes to avoid'],
    },
    'explainer': {
        'label': 'Explainer', 'plural': 'explainers',
        'format': 'Definition first, then how it works',
        'angle': 'Explain it clearly for someone new to the topic.',
        'as_second': 'Open with a plain definition, since explainer pages rank here too.',
        'elements': ['A plain one or two sentence definition near the top',
                     'How it works, broken into parts',
                     'Real examples'],
    },
    'listicle': {
        'label': 'List article', 'plural': 'list articles',
        'format': 'Numbered list',
        'angle': 'Give the reader a scannable set of options or tips.',
        'as_second': 'Consider a numbered section, since list articles rank here too.',
        'elements': ['A number in the title',
                     'A short take on each item',
                     'A quick pick for different readers'],
    },
    'comparison': {
        'label': 'Comparison article', 'plural': 'comparison articles',
        'format': 'Side-by-side comparison',
        'angle': 'Help the reader choose between specific options.',
        'as_second': 'Add a short comparison of the main options, since comparison pages rank here too.',
        'elements': ['A comparison table', 'Who each option suits', 'A clear verdict'],
    },
    'review': {
        'label': 'Review', 'plural': 'reviews',
        'format': 'Structured review',
        'angle': 'Share a first-hand evaluation.',
        'as_second': 'Include first-hand evaluation, since reviews rank here too.',
        'elements': ['First-hand findings', 'Pros and cons', 'A verdict'],
    },
    'service_page': {
        'label': 'Service page', 'plural': 'service pages',
        'format': 'Offer page',
        'angle': 'Show what the service is, who it is for and what it costs.',
        'as_second': 'Also cover cost, timeline and what the reader gets, since pages selling this service rank here too.',
        'elements': ['What is included', 'Price or price range', 'Timeline',
                     'What the client walks away with'],
    },
    'product_page': {
        'label': 'Product page', 'plural': 'product pages',
        'format': 'Product page',
        'angle': 'Describe one product in detail.',
        'as_second': 'Mention specific products with prices, since product pages rank here too.',
        'elements': ['Product details', 'Pricing', 'A clear call to action'],
        'warning': 'Product pages lead these results. An article will struggle to rank, so consider a different search.',
    },
    'category_page': {
        'label': 'Category or directory page', 'plural': 'category or directory pages',
        'format': 'Listing page',
        'angle': 'Gather many options in one place.',
        'as_second': 'Cover several options, since directory pages rank here too.',
        'elements': ['Many options in one place', 'Groupings or filters', 'Short descriptions'],
        'warning': 'Store and directory pages lead these results. An article will struggle to rank, so consider a different search.',
    },
    'tool': {
        'label': 'Free tool', 'plural': 'tools',
        'format': 'Interactive tool',
        'angle': 'Give the reader something to use, not just read.',
        'as_second': 'Consider adding a template or checklist, since tools rank here too.',
        'elements': ['A working tool, template or checklist', 'A short guide to using it'],
        'warning': 'Tools lead these results. A plain article will struggle unless it includes something usable.',
    },
    'video': {
        'label': 'Video', 'plural': 'videos',
        'format': 'Video, or an article with an embedded video',
        'angle': 'Show it rather than tell it.',
        'as_second': 'Consider embedding a video, since video results rank here too.',
        'elements': ['A video or clear visuals', 'A written summary of each step'],
    },
    'forum_thread': {
        'label': 'Discussion-style article', 'plural': 'forum threads',
        'format': 'Q&A with first-hand answers',
        'angle': 'Answer the questions real people ask, from experience.',
        'as_second': 'Include first-hand experience, since forum threads rank here too. That usually means good content is scarce for this search.',
        'elements': ['Real questions people ask', 'Direct answers from experience',
                     'Trade-offs, not just upsides'],
    },
    'news_article': {
        'label': 'News or timely update', 'plural': 'news articles',
        'format': 'News-style update',
        'angle': 'Cover what changed and why it matters now.',
        'as_second': 'Mention recent developments with dates, since news ranks here too.',
        'elements': ['What happened', 'Why it matters', 'A visible date'],
    },
    'research_paper': {
        'label': 'In-depth research piece', 'plural': 'research papers',
        'format': 'Long-form article with sources',
        'angle': 'Go deep and cite your sources.',
        'as_second': 'Cite research and data, since academic sources rank here too.',
        'elements': ['Cited sources', 'Data or findings', 'How the findings were reached'],
    },
    'program_page': {
        'label': 'Program or course page', 'plural': 'program and course pages',
        'format': 'Program page',
        'angle': 'Show who the training is for and what it covers.',
        'as_second': 'Mention relevant courses or certifications, since program pages rank here too.',
        'elements': ['Who it is for', 'What it covers', 'Cost and time commitment'],
        'warning': 'Course and certification pages lead these results, which usually means people want training rather than an article.',
    },
    'other': {
        'label': 'General article', 'plural': 'other pages',
        'format': 'Article',
        'angle': 'Cover the topic clearly.',
        'as_second': '',
        'elements': ['A clear answer to the search'],
    },
}


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
                user_intent: Dict[str, Any] = None,
                serp_features: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main analysis method - returns content strategy recommendations
        """
        analysis = {
            'query': query,
            'total_results_analyzed': len(results),
            'results': results,
        }
        
        # Page types from the classifier drive the recommendation when available
        analysis['page_types'] = self._analyze_page_types(results)
        analysis['serp_features'] = serp_features or {}
        analysis['community_count'] = self._count_community_results(results)
        
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
        
        # The results are already stored at the top level of the export, so don't duplicate them here
        analysis.pop('results', None)
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
        page_types = analysis.get('page_types', {})
        
        if page_types.get('ranked'):
            rec = self._recommend_from_page_types(page_types)
        else:
            # Fallback when classification was skipped: keyword scoring on titles and snippets
            rec = self._recommend_from_keywords(analysis, user_intent)
        
        self._apply_serp_features(rec, analysis.get('serp_features', {}),
                                  analysis.get('total_results_analyzed', 0))
        rec['competition'] = self._describe_competition(analysis)
        return rec
    
    # Sites where regular people post. Their presence in the top 10 means content supply is thin.
    COMMUNITY_DOMAINS = ('reddit.com', 'quora.com', 'medium.com', 'substack.com',
                         'linkedin.com/pulse', 'linkedin.com/posts', 'stackexchange.com',
                         'facebook.com/groups', 'community.')
    # Domain endings that always mean a government, university or international body
    INSTITUTION_SUFFIXES = ('.gov', '.edu', '.int', '.mil')
    # Platforms where the content belongs to an individual creator, so the platform's size doesn't count
    CREATOR_PLATFORMS = ('youtube.com', 'tiktok.com', 'instagram.com', 'x.com', 'twitter.com')
    
    def _is_community(self, r: Dict[str, Any]) -> bool:
        url = (r.get('url') or '').lower()
        is_forum = r.get('classification', {}).get('page_type') == 'forum_thread'
        return is_forum or any(d in url for d in self.COMMUNITY_DOMAINS)
    
    def _brand_tier(self, r: Dict[str, Any]) -> str:
        """household, established or small. Community posts and creator videos count as small."""
        if self._is_community(r):
            return 'small'  # a Reddit or LinkedIn post is someone's personal post, not the platform's
        host = urlparse(r.get('url') or '').netloc.lower()
        if any(host == p or host.endswith('.' + p) for p in self.CREATOR_PLATFORMS):
            return 'small'
        if any(host.endswith(s) or f"{s}." in host for s in self.INSTITUTION_SUFFIXES):
            return 'household'
        tier = r.get('classification', {}).get('brand_tier', 'small')
        return tier if tier in ('household', 'established') else 'small'
    
    def _count_community_results(self, results: List[Dict[str, Any]]) -> int:
        """Count forum, Q&A and self-published results in the top results"""
        return sum(1 for r in results if self._is_community(r))
    
    def _describe_competition(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Describe who ranks, without predicting whether a given writer can rank.
        That depends mostly on the writer's own site, which this tool cannot see.
        """
        results = analysis.get('results', [])
        total = len(results)
        community = analysis.get('community_count', 0)
        tiers = [(r, self._brand_tier(r)) for r in results]
        household = [r for r, t in tiers if t == 'household']
        established = [r for r, t in tiers if t == 'established']
        strong = len(household) + len(established)
        
        def domains(rows):
            out = []
            for r in rows:
                d = urlparse(r.get('url') or '').netloc.lower().replace('www.', '')
                if d and d not in out:
                    out.append(d)
            return out
        
        if strong == 0:
            who = f"No big names or established brands rank in the top {total}"
        else:
            who = f"Big names hold {len(household)} and established brands hold {len(established)} of the top {total}"
        forum_note = ""
        if community:
            forum_note = (f" {community} forum or community "
                          f"{'post ranks' if community == 1 else 'posts rank'}, which usually means good content is scarce.")
        
        # Forum posts are mentioned as a signal but do not change the level
        if len(household) >= 4 or strong >= 7:
            level = 'Crowded'
            summary = f"{who}." + forum_note
        elif strong <= 3:
            level = 'Open'
            summary = f"{who}. Smaller sites hold most of the top spots." + forum_note
        else:
            level = 'Mixed'
            summary = f"{who}, alongside smaller sites. The top spots are contested." + forum_note
        
        # What each level means for a writer, phrased as conditions rather than a prediction
        meaning = {
            'Open': "A newer site has a realistic chance here.",
            'Mixed': "Worth it if your piece is clearly better than what already ranks.",
            'Crowded': ("Best for sites that already have authority on this topic. "
                        "Otherwise, try a narrower related search."),
        }[level]
        
        return {
            'level': level,
            'meaning': meaning,
            'summary': summary,
            'big_names': len(household),
            'established': len(established),
            'community': community,
            'big_name_domains': domains(household),
            'established_domains': domains(established),
        }
    
    def _analyze_page_types(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Count the page types the classifier assigned to each result"""
        types = [r.get('classification', {}).get('page_type') for r in results]
        types = [t for t in types if t in PAGE_TYPE_PROFILES]
        counts = Counter(types)
        ranked = [(t, c) for t, c in counts.most_common() if t != 'other']
        return {'counts': dict(counts), 'ranked': ranked, 'total': len(types)}
    
    def _recommend_from_page_types(self, page_types: Dict[str, Any]) -> Dict[str, Any]:
        """Build the recommendation from the most common page types in the top results"""
        ranked = page_types['ranked']
        total = page_types['total']
        
        top_type, top_count = ranked[0]
        top = PAGE_TYPE_PROFILES[top_type]
        # Forum threads count as a competition signal, not a format to copy, so they are never blended in
        runners_up = [(t, c) for t, c in ranked[1:] if t != 'forum_thread']
        second_type, second_count = runners_up[0] if runners_up else (None, 0)
        
        # Blend in the runner-up when it holds at least 2 spots and a quarter of the results
        is_hybrid = second_type is not None and second_count >= 2 and second_count / total >= 0.25
        
        elements = list(top['elements'])
        reasoning = []
        
        if is_hybrid:
            second = PAGE_TYPE_PROFILES[second_type]
            content_type = f"{top['label']} with {second['label'].lower()} elements"
            angle = f"{top['angle']} {second['as_second']}"
            elements += [e for e in second['elements'][:2] if e not in elements]
            confidence = (top_count + second_count) / total
            reasoning.append(
                f"{top_count} of {total} results are {top['plural']} "
                f"and {second_count} are {second['plural']}"
            )
        else:
            content_type = top['label']
            angle = top['angle']
            confidence = top_count / total
            reasoning.append(f"{top_count} of {total} results are {top['plural']}")
        
        if top.get('warning'):
            reasoning.append(top['warning'])
        
        return {
            'content_type': content_type,
            'format': top['format'],
            'angle': angle,
            'required_elements': elements,
            'reasoning': reasoning,
            'confidence': round(min(confidence, 0.95), 2),
            'page_type_counts': page_types['counts'],
            'format_summary': reasoning[0],
            'format_warning': top.get('warning', ''),
            # Plain headline for writers: just the leading format. The blend is explained in the angle.
            'headline': top['label'],
        }
    
    def _apply_serp_features(self, rec: Dict[str, Any], features: Dict[str, Any],
                             total_results: int) -> None:
        """Add what the SERP features say to the recommendation"""
        if not features:
            return
        
        rec['serp_features_present'] = features.get('present', [])
        
        paa = features.get('people_also_ask', [])
        if paa:
            rec['questions_to_answer'] = paa
            rec['required_elements'].append('Answer the People Also Ask questions (listed below)')
            questions_word = "question" if len(paa) == 1 else "questions"
            rec['reasoning'].append(
                f"Google shows {len(paa)} People Also Ask {questions_word}, a ready-made outline"
            )
        
        related = features.get('related_searches', [])
        if related:
            rec['related_searches'] = related
        
        aio = features.get('ai_overview')
        if aio:
            reason = ("Google shows an AI Overview for this search. Expect fewer clicks, "
                      "and aim to be one of the sources it cites")
            sources = aio.get('sources', []) if isinstance(aio, dict) else []
            domains = []
            for s in sources:
                d = s.get('domain', '')
                if d and d not in domains:
                    domains.append(d)
            if domains:
                reason += f". It currently cites {', '.join(domains[:5])}"
            rec['reasoning'].append(reason)
            rec['ai_overview_sources'] = sources
        
        if features.get('forums_count'):
            rec['reasoning'].append(
                "Google shows a Discussions and forums block, so people want real experience. "
                "First-hand examples will help"
            )
        
        if features.get('answer_box'):
            rec['required_elements'].insert(0, 'A short, direct answer in the first paragraph')
            rec['reasoning'].append(
                "Google shows a featured answer at the top. A short, direct answer early on can win it"
            )
        
        if features.get('top_stories_count'):
            rec['reasoning'].append("News stories appear for this search, so freshness matters")
        
        if features.get('videos_count'):
            rec['reasoning'].append("Video results appear. An embedded video could help")
    
    def _recommend_from_keywords(self, analysis: Dict[str, Any],
                                 user_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Original keyword-based recommendation, used only when page types are unavailable"""
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
