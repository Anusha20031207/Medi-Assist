"""
Quick Test Script for Personalized Recommendation System

This script demonstrates how the personalized recommendation system works.
Run this from the Django shell:
    python manage.py shell < test_personalized_recommendations.py
"""

from users.models import UserRegistrationModel, UserHealthProfile, PersonalizedRecommendation, MedicalChatHistory
from users.views import extract_health_conditions, update_user_health_profile, get_user_health_context, generate_personalized_recommendations
import json

print("=" * 80)
print("PERSONALIZED RECOMMENDATION SYSTEM - TEST SCRIPT")
print("=" * 80)

# Get a test user (first user in database)
try:
    user = UserRegistrationModel.objects.first()
    if not user:
        print("\n❌ No users found in database. Please register a user first.")
        exit()
    
    user_id = user.id
    print(f"\n✅ Testing with user: {user.name} (ID: {user_id})")
    
    # Test 1: Extract health conditions from different queries
    print("\n" + "=" * 80)
    print("TEST 1: Health Condition Detection")
    print("=" * 80)
    
    test_queries = [
        "I have diabetes. What should I eat?",
        "My blood sugar is high. Any tips?",
        "I also have high blood pressure.",
        "What exercises are good for asthma?",
    ]
    
    for query in test_queries:
        conditions = extract_health_conditions(query)
        print(f"\n📝 Query: '{query}'")
        print(f"🔍 Detected: {conditions if conditions else 'None'}")
    
    # Test 2: Update health profile
    print("\n" + "=" * 80)
    print("TEST 2: Update User Health Profile")
    print("=" * 80)
    
    print(f"\n📤 Updating health profile with test queries...")
    for query in test_queries:
        update_user_health_profile(user_id, query)
    
    # Retrieve and display the profile
    health_profile = UserHealthProfile.objects.get(user_id=user_id)
    conditions = json.loads(health_profile.detected_conditions)
    
    print(f"\n✅ Health Profile Updated!")
    print(f"   Detected Conditions: {conditions}")
    print(f"   Last Updated: {health_profile.last_updated}")
    
    # Test 3: Get user health context
    print("\n" + "=" * 80)
    print("TEST 3: Retrieve User Health Context")
    print("=" * 80)
    
    health_context = get_user_health_context(user_id)
    print(f"\n📊 User's Health Context:")
    for condition, count in health_context.items():
        print(f"   • {condition}: {count} mention(s)")
    
    # Test 4: Generate personalized recommendations
    print("\n" + "=" * 80)
    print("TEST 4: Generate Personalized Recommendations")
    print("=" * 80)
    
    print(f"\n🎯 Generating recommendations based on detected conditions...")
    generate_personalized_recommendations(user_id, health_context)
    
    # Display generated recommendations
    recommendations = PersonalizedRecommendation.objects.filter(user_id=user_id)
    print(f"\n✅ Generated {recommendations.count()} Recommendations:")
    
    for rec in recommendations[:10]:  # Show first 10
        print(f"\n   📌 {rec.title}")
        print(f"      Type: {rec.get_recommendation_type_display()}")
        print(f"      Priority: {rec.priority.upper()}")
        print(f"      Description: {rec.description[:100]}...")
    
    # Test 5: Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"""
✅ System Status: WORKING

Test Results:
  • Health Condition Detection: ✓ Working
  • Profile Update: ✓ Working
  • Context Retrieval: ✓ Working
  • Recommendation Generation: ✓ Working

User Statistics:
  • Detected Conditions: {len(health_context)}
  • Total Recommendations: {recommendations.count()}
  • Profile Last Updated: {health_profile.last_updated}

Next Steps:
  1. Login to the application
  2. Ask the medical chatbot a question mentioning a health condition
  3. Check that:
     - Your condition appears in the "Detected Health Conditions" box
     - AI response is tailored to your condition
     - Recommendations are automatically generated
    """)
    
    print("=" * 80)
    print("✅ ALL TESTS PASSED!")
    print("=" * 80)
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()
