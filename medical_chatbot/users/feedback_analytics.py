"""
Feedback Analytics Module
Provides data analytics techniques for analyzing user feedback
Includes: Sentiment Analysis, Rating Distribution, Trend Analysis, Word Frequency, and Clustering
"""

from django.db.models import Avg, Count, Q
from datetime import datetime, timedelta
import json
import re
from collections import Counter, defaultdict
from .models import FeedbackModel, UserRegistrationModel
import numpy as np
from typing import Dict, List, Tuple

try:
    from textblob import TextBlob
    HAS_TEXTBLOB = True
except ImportError:
    HAS_TEXTBLOB = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class FeedbackAnalyticsEngine:
    """Main class for analyzing feedback data"""
    
    def __init__(self, days_back=30):
        """
        Initialize the analytics engine
        
        Args:
            days_back: Number of days to analyze (default: 30 days)
        """
        self.days_back = days_back
        self.start_date = datetime.now() - timedelta(days=days_back)
        self.feedback_data = FeedbackModel.objects.filter(
            created_at__gte=self.start_date
        ).select_related('user')
    
    # ============== BASIC STATISTICS ==============
    
    def get_basic_statistics(self) -> Dict:
        """
        Get basic statistics about feedback
        
        Returns:
            Dictionary with basic metrics
        """
        total_feedbacks = self.feedback_data.count()
        
        if total_feedbacks == 0:
            return {
                'total_feedbacks': 0,
                'average_rating': 0,
                'unique_users': 0,
                'rating_distribution': {}
            }
        
        rating_stats = self.feedback_data.aggregate(
            avg_rating=Avg('rating'),
            count=Count('id')
        )
        
        unique_users = self.feedback_data.values('user').distinct().count()
        
        # Rating distribution
        rating_dist = {}
        for i in range(1, 6):
            count = self.feedback_data.filter(rating=i).count()
            percentage = (count / total_feedbacks * 100) if total_feedbacks > 0 else 0
            rating_dist[i] = {
                'count': count,
                'percentage': round(percentage, 2)
            }
        
        return {
            'total_feedbacks': total_feedbacks,
            'average_rating': round(rating_stats['avg_rating'], 2) if rating_stats['avg_rating'] else 0,
            'unique_users': unique_users,
            'rating_distribution': rating_dist,
            'period_days': self.days_back
        }
    
    # ============== SENTIMENT ANALYSIS ==============
    
    def analyze_sentiment(self) -> Dict:
        """
        Perform sentiment analysis on feedback messages
        Uses TextBlob for polarity and subjectivity analysis
        
        Returns:
            Dictionary with sentiment metrics
        """
        if not HAS_TEXTBLOB:
            return {'error': 'TextBlob not installed. Install with: pip install textblob'}
        
        sentiments = {
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'polarity_scores': [],
            'subjectivity_scores': []
        }
        
        for feedback in self.feedback_data:
            combined_text = f"{feedback.subject} {feedback.message}"
            blob = TextBlob(combined_text)
            
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            sentiments['polarity_scores'].append(polarity)
            sentiments['subjectivity_scores'].append(subjectivity)
            
            # Classify sentiment
            if polarity > 0.1:
                sentiments['positive'] += 1
            elif polarity < -0.1:
                sentiments['negative'] += 1
            else:
                sentiments['neutral'] += 1
        
        total = sentiments['positive'] + sentiments['neutral'] + sentiments['negative']
        if total > 0:
            sentiments['positive_pct'] = round(sentiments['positive'] / total * 100, 2)
            sentiments['neutral_pct'] = round(sentiments['neutral'] / total * 100, 2)
            sentiments['negative_pct'] = round(sentiments['negative'] / total * 100, 2)
        
        # Calculate average polarity and subjectivity
        if sentiments['polarity_scores']:
            sentiments['avg_polarity'] = round(np.mean(sentiments['polarity_scores']), 3)
            sentiments['avg_subjectivity'] = round(np.mean(sentiments['subjectivity_scores']), 3)
            sentiments['polarity_scores'] = [round(x, 3) for x in sentiments['polarity_scores'][:10]]  # Sample
        
        return sentiments
    
    # ============== WORD FREQUENCY ANALYSIS ==============
    
    def get_word_frequency(self, top_n=20) -> Dict:
        """
        Analyze word frequency in feedback messages
        Removes common stop words
        
        Args:
            top_n: Number of top words to return
            
        Returns:
            Dictionary with word frequency data
        """
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'it', 'this', 'that', 'i',
            'you', 'we', 'they', 'he', 'she', 'what', 'which', 'who', 'when',
            'where', 'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more',
            'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same',
            'so', 'than', 'too', 'very', 'just'
        }
        
        words = []
        for feedback in self.feedback_data:
            combined_text = f"{feedback.subject} {feedback.message}".lower()
            # Remove special characters and split
            text_words = re.findall(r'\b[a-z]+\b', combined_text)
            words.extend([w for w in text_words if w not in stop_words and len(w) > 2])
        
        word_freq = Counter(words)
        top_words = word_freq.most_common(top_n)
        
        return {
            'total_unique_words': len(word_freq),
            'total_words': len(words),
            'top_words': [{'word': word, 'frequency': count} for word, count in top_words]
        }
    
    # ============== TREND ANALYSIS ==============
    
    def analyze_trends(self, interval='daily') -> Dict:
        """
        Analyze feedback trends over time
        
        Args:
            interval: 'daily', 'weekly', or 'monthly'
            
        Returns:
            Dictionary with trend data
        """
        trends = defaultdict(lambda: {'count': 0, 'avg_rating': 0, 'ratings': []})
        
        for feedback in self.feedback_data:
            if interval == 'daily':
                key = feedback.created_at.date()
            elif interval == 'weekly':
                key = feedback.created_at.isocalendar()[1]  # Week number
            elif interval == 'monthly':
                key = feedback.created_at.strftime('%Y-%m')
            else:
                key = feedback.created_at.date()
            
            trends[key]['count'] += 1
            trends[key]['ratings'].append(feedback.rating)
        
        # Calculate average ratings for each period
        result = {}
        for key, data in sorted(trends.items()):
            result[str(key)] = {
                'count': data['count'],
                'avg_rating': round(np.mean(data['ratings']), 2),
                'min_rating': min(data['ratings']),
                'max_rating': max(data['ratings'])
            }
        
        return {f'{interval}_trends': result}
    
    # ============== RATING ANALYSIS ==============
    
    def analyze_ratings(self) -> Dict:
        """
        Detailed analysis of ratings
        
        Returns:
            Dictionary with rating analysis
        """
        ratings = [f.rating for f in self.feedback_data]
        
        if not ratings:
            return {}
        
        return {
            'average_rating': round(np.mean(ratings), 2),
            'median_rating': float(np.median(ratings)),
            'std_deviation': round(np.std(ratings), 2),
            'min_rating': int(np.min(ratings)),
            'max_rating': int(np.max(ratings)),
            'rating_mode': int(Counter(ratings).most_common(1)[0][0])
        }
    
    # ============== SUBJECT CATEGORIZATION ==============
    
    def categorize_feedback_subjects(self) -> Dict:
        """
        Categorize feedback by subject using keyword matching
        
        Returns:
            Dictionary with subject categories
        """
        categories = {
            'Medical Chatbot': 0,
            'Nutrition Analysis': 0,
            'User Interface': 0,
            'Performance': 0,
            'Accuracy': 0,
            'Features': 0,
            'Other': 0
        }
        
        category_keywords = {
            'Medical Chatbot': ['chat', 'medical', 'doctor', 'diagnosis', 'disease', 'treatment'],
            'Nutrition Analysis': ['nutrition', 'food', 'diet', 'health', 'calories', 'nutrition'],
            'User Interface': ['interface', 'ui', 'layout', 'design', 'button', 'navigation'],
            'Performance': ['slow', 'fast', 'speed', 'performance', 'lag', 'responsive'],
            'Accuracy': ['accurate', 'correct', 'wrong', 'error', 'mistake', 'precision'],
            'Features': ['feature', 'function', 'capability', 'option', 'tool']
        }
        
        for feedback in self.feedback_data:
            combined = f"{feedback.subject} {feedback.message}".lower()
            categorized = False
            
            for category, keywords in category_keywords.items():
                if any(keyword in combined for keyword in keywords):
                    categories[category] += 1
                    categorized = True
                    break
            
            if not categorized:
                categories['Other'] += 1
        
        total = sum(categories.values())
        result = {}
        for cat, count in categories.items():
            percentage = (count / total * 100) if total > 0 else 0
            result[cat] = {
                'count': count,
                'percentage': round(percentage, 2)
            }
        
        return result
    
    # ============== CLUSTERING ANALYSIS ==============
    
    def cluster_feedback(self, n_clusters=3) -> Dict:
        """
        Cluster feedback messages using KMeans clustering
        Requires scikit-learn
        
        Args:
            n_clusters: Number of clusters
            
        Returns:
            Dictionary with cluster information
        """
        if not HAS_SKLEARN:
            return {'error': 'scikit-learn not installed. Install with: pip install scikit-learn'}
        
        if self.feedback_data.count() < n_clusters:
            return {'error': f'Need at least {n_clusters} feedbacks for clustering'}
        
        messages = [f"{fb.subject} {fb.message}" for fb in self.feedback_data]
        
        try:
            vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
            X = vectorizer.fit_transform(messages)
            
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X)
            
            cluster_data = defaultdict(list)
            for idx, cluster_id in enumerate(clusters):
                feedback = list(self.feedback_data)[idx]
                cluster_data[int(cluster_id)].append({
                    'subject': feedback.subject,
                    'rating': feedback.rating,
                    'date': str(feedback.created_at.date())
                })
            
            result = {}
            for cluster_id, feedbacks in cluster_data.items():
                result[f'cluster_{cluster_id}'] = {
                    'size': len(feedbacks),
                    'avg_rating': round(np.mean([f['rating'] for f in feedbacks]), 2),
                    'sample_feedbacks': feedbacks[:3]
                }
            
            return result
        except Exception as e:
            return {'error': str(e)}
    
    # ============== USER ENGAGEMENT ANALYSIS ==============
    
    def analyze_user_engagement(self) -> Dict:
        """
        Analyze user engagement patterns
        
        Returns:
            Dictionary with engagement metrics
        """
        user_feedback_count = self.feedback_data.values('user').annotate(
            count=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('-count')
        
        power_users = user_feedback_count.filter(count__gte=3).count()
        active_users = user_feedback_count.count()
        
        top_users = []
        for user_stat in user_feedback_count[:5]:
            user = UserRegistrationModel.objects.get(id=user_stat['user'])
            top_users.append({
                'user_name': user.name,
                'feedback_count': user_stat['count'],
                'avg_rating': round(user_stat['avg_rating'], 2)
            })
        
        return {
            'total_unique_users': active_users,
            'power_users': power_users,
            'avg_feedbacks_per_user': round(
                self.feedback_data.count() / active_users if active_users > 0 else 0, 2
            ),
            'top_contributors': top_users
        }
    
    # ============== COMPREHENSIVE REPORT ==============
    
    def generate_comprehensive_report(self) -> Dict:
        """
        Generate a comprehensive feedback analysis report
        
        Returns:
            Dictionary containing all analysis results
        """
        report = {
            'generated_at': str(datetime.now()),
            'analysis_period': {
                'start_date': str(self.start_date.date()),
                'end_date': str(datetime.now().date()),
                'days': self.days_back
            },
            'basic_statistics': self.get_basic_statistics(),
            'rating_analysis': self.analyze_ratings(),
            'sentiment_analysis': self.analyze_sentiment(),
            'word_frequency': self.get_word_frequency(),
            'feedback_categories': self.categorize_feedback_subjects(),
            'user_engagement': self.analyze_user_engagement(),
            'daily_trends': self.analyze_trends('daily'),
            'feedback_clustering': self.cluster_feedback(n_clusters=3)
        }
        
        return report
    
    # ============== EXPORT FUNCTIONALITY ==============
    
    def export_to_json(self, report: Dict) -> str:
        """
        Export report to JSON format
        
        Args:
            report: Report dictionary
            
        Returns:
            JSON string
        """
        return json.dumps(report, indent=2, default=str)
    
    def get_summary_insights(self) -> Dict:
        """
        Get key insights from feedback analysis
        
        Returns:
            Dictionary with actionable insights
        """
        stats = self.get_basic_statistics()
        sentiment = self.analyze_sentiment()
        categories = self.categorize_feedback_subjects()
        engagement = self.analyze_user_engagement()
        
        insights = {
            'overall_satisfaction': 'High' if stats['average_rating'] >= 4 else 'Medium' if stats['average_rating'] >= 3 else 'Low',
            'sentiment_trend': 'Positive' if sentiment.get('positive_pct', 0) > 50 else 'Mixed' if sentiment.get('neutral_pct', 0) > 30 else 'Negative',
            'top_issue_category': max(categories, key=lambda x: categories[x]['percentage']),
            'user_participation': f"{engagement['total_unique_users']} users ({engagement['power_users']} power users)",
            'key_feedback_themes': [item['word'] for item in self.get_word_frequency(top_n=5)['top_words']],
            'recommendations': self._generate_recommendations(stats, sentiment, categories)
        }
        
        return insights
    
    def _generate_recommendations(self, stats: Dict, sentiment: Dict, categories: Dict) -> List[str]:
        """
        Generate actionable recommendations based on analysis
        
        Args:
            stats: Basic statistics
            sentiment: Sentiment analysis
            categories: Feedback categories
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Rating-based recommendations
        if stats['average_rating'] < 3:
            recommendations.append("⚠️ Overall satisfaction is low. Prioritize addressing major issues.")
        
        if 'negative_pct' in sentiment and sentiment['negative_pct'] > 30:
            recommendations.append("⚠️ High percentage of negative feedback. Focus on problem areas.")
        
        # Category-based recommendations
        top_category = max(categories, key=lambda x: categories[x]['percentage'])
        if categories[top_category]['percentage'] > 40:
            recommendations.append(f"📌 '{top_category}' is the dominant feedback topic. Consider improvements here.")
        
        # Positive feedback recommendation
        if 'positive_pct' in sentiment and sentiment['positive_pct'] > 60:
            recommendations.append("✅ Strong positive feedback. Maintain current quality standards.")
        
        if not recommendations:
            recommendations.append("📊 Feedback is balanced. Continue monitoring for changes.")
        
        return recommendations


def get_feedback_analytics(days_back=30) -> Dict:
    """
    Convenience function to get analytics report
    
    Args:
        days_back: Number of days to analyze
        
    Returns:
        Comprehensive analytics report
    """
    engine = FeedbackAnalyticsEngine(days_back=days_back)
    return engine.generate_comprehensive_report()


def get_feedback_insights(days_back=30) -> Dict:
    """
    Convenience function to get summary insights
    
    Args:
        days_back: Number of days to analyze
        
    Returns:
        Key insights and recommendations
    """
    engine = FeedbackAnalyticsEngine(days_back=days_back)
    return engine.get_summary_insights()
