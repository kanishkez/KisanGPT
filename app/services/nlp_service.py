import re
import logging
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class NLPService:
    def __init__(self):
        # Agricultural domain knowledge base
        self.crop_keywords = {
            'wheat': ['wheat', 'gehun', 'गेहूं', 'triticum', 'rabi'],
            'rice': ['rice', 'chawal', 'चावल', 'paddy', 'basmati', 'kharif'],
            'cotton': ['cotton', 'kapas', 'कपास', 'bt cotton', 'fiber'],
            'maize': ['maize', 'corn', 'makka', 'मक्का', 'bhutta'],
            'sugarcane': ['sugarcane', 'ganna', 'गन्ना', 'sugar'],
            'potato': ['potato', 'aloo', 'आलू', 'tuber'],
            'onion': ['onion', 'pyaz', 'प्याज'],
            'tomato': ['tomato', 'tamatar', 'टमाटर'],
            'pulses': ['dal', 'दाल', 'arhar', 'moong', 'chana', 'lentil', 'pulse'],
            'soybean': ['soybean', 'soya', 'सोयाबीन']
        }
        
        self.location_keywords = {
            'punjab': ['punjab', 'पंजाब', 'chandigarh', 'ludhiana', 'amritsar'],
            'haryana': ['haryana', 'हरियाणा', 'gurgaon', 'faridabad', 'hisar'],
            'uttar pradesh': ['uttar pradesh', 'up', 'उत्तर प्रदेश', 'lucknow', 'kanpur'],
            'maharashtra': ['maharashtra', 'महाराष्ट्र', 'mumbai', 'pune', 'nashik'],
            'gujarat': ['gujarat', 'गुजरात', 'ahmedabad', 'surat', 'vadodara'],
            'rajasthan': ['rajasthan', 'राजस्थान', 'jaipur', 'jodhpur', 'udaipur'],
            'madhya pradesh': ['madhya pradesh', 'mp', 'मध्य प्रदेश', 'bhopal', 'indore'],
            'karnataka': ['karnataka', 'कर्नाटक', 'bangalore', 'mysore', 'hubli'],
            'andhra pradesh': ['andhra pradesh', 'ap', 'आंध्र प्रदेश', 'hyderabad', 'vijayawada'],
            'telangana': ['telangana', 'तेलंगाना', 'hyderabad', 'warangal'],
            'tamil nadu': ['tamil nadu', 'तमिल नाडु', 'chennai', 'coimbatore', 'madurai'],
            'west bengal': ['west bengal', 'पश्चिम बंगाल', 'kolkata', 'howrah'],
            'bihar': ['bihar', 'बिहार', 'patna', 'gaya', 'muzaffarpur'],
            'odisha': ['odisha', 'ओडिशा', 'bhubaneswar', 'cuttack']
        }
        
        self.intent_patterns = {
            'crop_recommendation': [
                'what crop', 'which crop', 'best crop', 'recommend crop', 'grow crop',
                'suitable crop', 'profitable crop', 'crop for', 'farming advice',
                'cultivation', 'sowing', 'planting', 'agriculture'
            ],
            'market_prices': [
                'price', 'rate', 'market', 'mandi', 'cost', 'selling price',
                'current price', 'market rate', 'commodity price', 'trading'
            ],
            'weather_info': [
                'weather', 'climate', 'rain', 'monsoon', 'temperature',
                'humidity', 'forecast', 'seasonal', 'drought', 'flood'
            ],
            'farming_practices': [
                'how to grow', 'cultivation method', 'farming technique',
                'best practice', 'fertilizer', 'pesticide', 'irrigation',
                'soil preparation', 'harvesting', 'storage'
            ],
            'disease_pest': [
                'disease', 'pest', 'insect', 'fungus', 'virus', 'infection',
                'treatment', 'control', 'management', 'protection'
            ],
            'government_schemes': [
                'scheme', 'subsidy', 'government', 'policy', 'support',
                'loan', 'insurance', 'msp', 'procurement', 'kisan'
            ]
        }
        
        # Initialize TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            max_features=1000
        )
        
        # Prepare corpus for similarity matching
        self._prepare_corpus()
    
    def _prepare_corpus(self):
        """Prepare corpus for TF-IDF vectorization"""
        corpus = []
        
        # Add crop-related sentences
        for crop, keywords in self.crop_keywords.items():
            corpus.extend([f"grow {crop}", f"cultivate {crop}", f"plant {crop}"])
        
        # Add location-related sentences
        for location, keywords in self.location_keywords.items():
            corpus.extend([f"farming in {location}", f"agriculture {location}"])
        
        # Add intent-related sentences
        for intent, patterns in self.intent_patterns.items():
            corpus.extend(patterns)
        
        # Fit vectorizer
        try:
            self.vectorizer.fit(corpus)
            self.corpus_vectors = self.vectorizer.transform(corpus)
        except Exception as e:
            logger.error(f"Error preparing NLP corpus: {e}")
    
    def analyze_query(self, query: str) -> Dict:
        """Analyze user query using NLP to extract intent, entities, and context"""
        query_lower = query.lower()
        
        analysis = {
            'original_query': query,
            'intent': self._extract_intent(query_lower),
            'crops': self._extract_crops(query_lower),
            'locations': self._extract_locations(query_lower),
            'context_score': self._calculate_context_relevance(query_lower),
            'data_requirements': self._determine_data_requirements(query_lower),
            'confidence': 0.0
        }
        
        # Calculate overall confidence
        analysis['confidence'] = self._calculate_confidence(analysis)
        
        return analysis
    
    def _extract_intent(self, query: str) -> List[str]:
        """Extract user intent from query"""
        intents = []
        
        for intent, patterns in self.intent_patterns.items():
            score = 0
            for pattern in patterns:
                if pattern in query:
                    score += 1
                # Check for partial matches
                elif any(word in query.split() for word in pattern.split()):
                    score += 0.5
            
            if score > 0:
                intents.append((intent, score))
        
        # Sort by score and return top intents
        intents.sort(key=lambda x: x[1], reverse=True)
        return [intent[0] for intent in intents[:3]]
    
    def _extract_crops(self, query: str) -> List[str]:
        """Extract crop names from query"""
        detected_crops = []
        
        for crop, keywords in self.crop_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    detected_crops.append(crop)
                    break
        
        return list(set(detected_crops))
    
    def _extract_locations(self, query: str) -> List[str]:
        """Extract location names from query"""
        detected_locations = []
        
        for location, keywords in self.location_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    detected_locations.append(location)
                    break
        
        return list(set(detected_locations))
    
    def _calculate_context_relevance(self, query: str) -> float:
        """Calculate how relevant the query is to agriculture using TF-IDF similarity"""
        try:
            query_vector = self.vectorizer.transform([query])
            similarities = cosine_similarity(query_vector, self.corpus_vectors)
            return float(np.max(similarities))
        except Exception as e:
            logger.error(f"Error calculating context relevance: {e}")
            return 0.5  # Default moderate relevance
    
    def _determine_data_requirements(self, query: str) -> Dict[str, bool]:
        """Determine what data should be fetched based on query analysis"""
        requirements = {
            'market_data': False,
            'weather_data': False,
            'crop_data': False,
            'news_data': False,
            'regional_data': False
        }
        
        # Market data requirements
        if any(word in query for word in ['price', 'rate', 'market', 'mandi', 'cost', 'sell']):
            requirements['market_data'] = True
        
        # Weather data requirements
        if any(word in query for word in ['weather', 'rain', 'climate', 'monsoon', 'temperature']):
            requirements['weather_data'] = True
        
        # Crop data requirements
        if any(word in query for word in ['crop', 'grow', 'plant', 'cultivate', 'farming']):
            requirements['crop_data'] = True
        
        # News data requirements
        if any(word in query for word in ['news', 'update', 'scheme', 'policy', 'government']):
            requirements['news_data'] = True
        
        # Regional data requirements
        if any(location in query for location in self.location_keywords.keys()):
            requirements['regional_data'] = True
        
        return requirements
    
    def _calculate_confidence(self, analysis: Dict) -> float:
        """Calculate overall confidence in the analysis"""
        confidence_factors = []
        
        # Intent confidence
        if analysis['intent']:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.3)
        
        # Entity extraction confidence
        if analysis['crops'] or analysis['locations']:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.4)
        
        # Context relevance
        confidence_factors.append(analysis['context_score'])
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def should_fetch_data(self, analysis: Dict, data_type: str) -> bool:
        """Determine if specific data should be fetched based on analysis"""
        requirements = analysis.get('data_requirements', {})
        confidence = analysis.get('confidence', 0.0)
        
        # Only fetch data if confidence is reasonable and requirement is detected
        return requirements.get(data_type, False) and confidence > 0.3
    
    def get_enhanced_context_prompt(self, analysis: Dict, context_data: Dict) -> str:
        """Generate enhanced context prompt for the LLM based on NLP analysis"""
        prompt_parts = []
        
        # Add query analysis
        prompt_parts.append("## Query Analysis:")
        prompt_parts.append(f"User Intent: {', '.join(analysis['intent']) if analysis['intent'] else 'General inquiry'}")
        
        if analysis['crops']:
            prompt_parts.append(f"Crops of Interest: {', '.join(analysis['crops'])}")
        
        if analysis['locations']:
            prompt_parts.append(f"Locations: {', '.join(analysis['locations'])}")
        
        prompt_parts.append(f"Agricultural Relevance: {analysis['context_score']:.2f}")
        
        # Add relevant context data
        if context_data.get('market_data'):
            prompt_parts.append("\n## Market Data:")
            prompt_parts.append(str(context_data['market_data']))
        
        if context_data.get('weather_data'):
            prompt_parts.append("\n## Weather Information:")
            prompt_parts.append(str(context_data['weather_data']))
        
        if context_data.get('news_data'):
            prompt_parts.append("\n## Recent Agricultural News:")
            prompt_parts.append(str(context_data['news_data']))
        
        return "\n".join(prompt_parts)
