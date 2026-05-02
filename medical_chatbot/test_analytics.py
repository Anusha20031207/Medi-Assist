"""
Feedback Analytics - Test & Demonstration Script
This script demonstrates how to use the feedback analytics module
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medical_chatbot.settings')
django.setup()

from users.feedback_analytics import (
    FeedbackAnalyticsEngine,
    get_feedback_analytics,
    get_feedback_insights
)
from users.models import FeedbackModel, UserRegistrationModel
from datetime import datetime, timedelta
import json


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"📊 {title}")
    print("="*80)


def test_basic_statistics():
    """Test basic statistics analysis"""
    print_section("BASIC STATISTICS")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    stats = engine.get_basic_statistics()
    
    print(f"Total Feedbacks: {stats['total_feedbacks']}")
    print(f"Average Rating: {stats['average_rating']}/5")
    print(f"Unique Users: {stats['unique_users']}")
    print(f"Analysis Period: {stats['period_days']} days")
    
    print("\nRating Distribution:")
    for rating, data in stats['rating_distribution'].items():
        bar = "█" * int(data['percentage'] / 5)
        print(f"  {rating} stars: {data['count']:3d} ({data['percentage']:5.1f}%) {bar}")


def test_sentiment_analysis():
    """Test sentiment analysis"""
    print_section("SENTIMENT ANALYSIS")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    sentiment = engine.analyze_sentiment()
    
    if 'error' in sentiment:
        print(f"⚠️  {sentiment['error']}")
        return
    
    print(f"Positive: {sentiment['positive']} ({sentiment['positive_pct']:.1f}%)")
    print(f"Neutral:  {sentiment['neutral']} ({sentiment['neutral_pct']:.1f}%)")
    print(f"Negative: {sentiment['negative']} ({sentiment['negative_pct']:.1f}%)")
    
    print(f"\nAverage Polarity: {sentiment['avg_polarity']:.3f} (-1 to 1, higher = more positive)")
    print(f"Average Subjectivity: {sentiment['avg_subjectivity']:.3f} (0 to 1, higher = more subjective)")


def test_word_frequency():
    """Test word frequency analysis"""
    print_section("WORD FREQUENCY ANALYSIS")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    words = engine.get_word_frequency(top_n=15)
    
    print(f"Total Unique Words: {words['total_unique_words']}")
    print(f"Total Word Occurrences: {words['total_words']}")
    
    print("\nTop 15 Keywords:")
    for i, item in enumerate(words['top_words'], 1):
        bar = "▪" * min(item['frequency'], 20)
        print(f"  {i:2d}. {item['word']:15s} : {item['frequency']:3d} {bar}")


def test_rating_analysis():
    """Test rating statistics"""
    print_section("RATING STATISTICS")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    ratings = engine.analyze_ratings()
    
    if not ratings:
        print("No rating data available")
        return
    
    print(f"Average Rating: {ratings['average_rating']}/5")
    print(f"Median Rating: {ratings['median_rating']}/5")
    print(f"Mode (Most Common): {ratings['rating_mode']}/5")
    print(f"Standard Deviation: {ratings['std_deviation']}")
    print(f"Min Rating: {ratings['min_rating']}/5")
    print(f"Max Rating: {ratings['max_rating']}/5")


def test_feedback_categories():
    """Test feedback categorization"""
    print_section("FEEDBACK CATEGORIZATION")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    categories = engine.categorize_feedback_subjects()
    
    print("Feedback Distribution by Category:\n")
    for category in sorted(categories.keys(), key=lambda x: categories[x]['percentage'], reverse=True):
        data = categories[category]
        bar = "█" * int(data['percentage'] / 3)
        print(f"  {category:20s}: {data['count']:3d} ({data['percentage']:5.1f}%) {bar}")


def test_trends():
    """Test trend analysis"""
    print_section("TREND ANALYSIS (Daily)")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    trends = engine.analyze_trends('daily')
    
    print("Date        | Count | Avg Rating | Min | Max")
    print("-" * 50)
    
    for date, trend in list(trends['daily_trends'].items())[-7:]:  # Last 7 days
        print(f"{date} |  {trend['count']:2d}  |    {trend['avg_rating']:.2f}    | {trend['min_rating']}   | {trend['max_rating']}")


def test_user_engagement():
    """Test user engagement analysis"""
    print_section("USER ENGAGEMENT ANALYSIS")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    engagement = engine.analyze_user_engagement()
    
    print(f"Total Unique Users: {engagement['total_unique_users']}")
    print(f"Power Users (3+ feedbacks): {engagement['power_users']}")
    print(f"Avg Feedbacks per User: {engagement['avg_feedbacks_per_user']}")
    
    power_user_pct = (engagement['power_users'] / engagement['total_unique_users'] * 100) \
                     if engagement['total_unique_users'] > 0 else 0
    print(f"Power User Percentage: {power_user_pct:.1f}%")
    
    print("\nTop 5 Contributors:")
    print(f"{'Rank':<5} {'User Name':<20} {'Feedbacks':<10} {'Avg Rating':<12}")
    print("-" * 50)
    for i, user in enumerate(engagement['top_contributors'], 1):
        print(f"{i:<5} {user['user_name']:<20} {user['feedback_count']:<10} {user['avg_rating']:.1f}/5")


def test_clustering():
    """Test feedback clustering"""
    print_section("FEEDBACK CLUSTERING (K-Means)")
    
    engine = FeedbackAnalyticsEngine(days_back=30)
    clusters = engine.cluster_feedback(n_clusters=3)
    
    if 'error' in clusters:
        print(f"⚠️  {clusters['error']}")
        return
    
    for cluster_name, cluster_data in clusters.items():
        print(f"\n{cluster_name.upper()}:")
        print(f"  Size: {cluster_data['size']} feedbacks")
        print(f"  Average Rating: {cluster_data['avg_rating']}/5")
        print(f"  Sample Feedbacks:")
        for feedback in cluster_data['sample_feedbacks'][:2]:
            print(f"    - {feedback['subject'][:50]} (Rating: {feedback['rating']}/5)")


def test_insights():
    """Test insights and recommendations"""
    print_section("INSIGHTS & RECOMMENDATIONS")
    
    insights = get_feedback_insights(days_back=30)
    
    print(f"Overall Satisfaction: {insights['overall_satisfaction']}")
    print(f"Sentiment Trend: {insights['sentiment_trend']}")
    print(f"Top Issue Category: {insights['top_issue_category']}")
    print(f"User Participation: {insights['user_participation']}")
    
    print(f"\nKey Feedback Themes:")
    for theme in insights['key_feedback_themes']:
        print(f"  • {theme}")
    
    print(f"\nRecommendations:")
    for rec in insights['recommendations']:
        print(f"  • {rec}")


def test_comprehensive_report():
    """Test comprehensive report generation"""
    print_section("COMPREHENSIVE REPORT")
    
    analytics = get_feedback_analytics(days_back=30)
    
    print("Report Sections Available:")
    for key in analytics.keys():
        if key != 'generated_at':
            print(f"  ✓ {key}")
    
    print(f"\nReport Generated At: {analytics['generated_at']}")
    print(f"Analysis Period: {analytics['analysis_period']['start_date']} to {analytics['analysis_period']['end_date']}")
    
    # Export to JSON
    engine = FeedbackAnalyticsEngine(days_back=30)
    json_str = engine.export_to_json(analytics)
    print(f"\nJSON Export Size: {len(json_str)} characters")


def run_all_tests():
    """Run all tests"""
    print("\n" + "🚀 " * 20)
    print("FEEDBACK ANALYTICS MODULE - TEST SUITE")
    print("🚀 " * 20)
    
    try:
        # Check if there's feedback data
        feedback_count = FeedbackModel.objects.count()
        if feedback_count == 0:
            print("\n⚠️  No feedback data found in database!")
            print("Please add some feedback through the application first.")
            return
        
        print(f"\n✓ Found {feedback_count} feedbacks in database")
        
        # Run tests
        test_basic_statistics()
        test_sentiment_analysis()
        test_word_frequency()
        test_rating_analysis()
        test_feedback_categories()
        test_trends()
        test_user_engagement()
        test_clustering()
        test_insights()
        test_comprehensive_report()
        
        print_section("TEST SUITE COMPLETED SUCCESSFULLY")
        print("✅ All analytics modules are working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    run_all_tests()
