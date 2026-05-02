from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import models
from users.forms import UserRegistrationForm, FeedbackForm
from .models import UserRegistrationModel, FeedbackModel, MedicalChatHistory, NutritionAnalysisHistory, PersonalizedRecommendation, HealthInsight, UserHealthProfile, DocumentChunk
from .security import hash_password, verify_password
from .ratelimit import rate_limit
from .rag import get_rag_context_for_query
import os, re, mimetypes, json
from datetime import datetime, timedelta
import google.generativeai as genai

# ---------------- Gemini Config ----------------
# Get API key from settings (which reads from .env file)
GEMINI_API_KEY = getattr(settings, "GOOGLE_API_KEY", None)
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# -------- Helper Functions for Personalized Recommendations --------
def extract_health_conditions(user_query):
    """Extract health conditions mentioned in user query"""
    conditions_map = {
        'diabetes': ['diabetes', 'diabetic', 'blood sugar', 'glucose', 'insulin'],
        'hypertension': ['hypertension', 'high blood pressure', 'bp', 'blood pressure'],
        'heart_disease': ['heart', 'cardiac', 'cholesterol', 'heart attack', 'heart disease'],
        'obesity': ['obesity', 'overweight', 'weight loss', 'excess weight'],
        'asthma': ['asthma', 'asthmatic', 'breathing', 'wheeze'],
        'arthritis': ['arthritis', 'joint pain', 'joint', 'rheumatoid'],
        'anxiety': ['anxiety', 'anxious', 'panic', 'worry'],
        'depression': ['depression', 'depressed', 'sad', 'low mood'],
        'insomnia': ['insomnia', 'sleep disorder', 'cannot sleep', 'sleepless'],
        'thyroid': ['thyroid', 'hyperthyroid', 'hypothyroid'],
        'migraine': ['migraine', 'headache', 'migraine attack'],
        'allergy': ['allergy', 'allergic', 'allergen', 'hay fever'],
    }
    
    detected = {}
    query_lower = user_query.lower()
    
    for condition, keywords in conditions_map.items():
        for keyword in keywords:
            if keyword in query_lower:
                detected[condition] = detected.get(condition, 0) + 1
    
    return detected


def update_user_health_profile(user_id, query_text):
    """Update user's health profile based on chat query"""
    try:
        health_profile, created = UserHealthProfile.objects.get_or_create(user_id=user_id)
        
        # Extract conditions
        detected_conditions = extract_health_conditions(query_text)
        
        if detected_conditions:
            # Update detected conditions
            existing_conditions = json.loads(health_profile.detected_conditions)
            
            for condition, count in detected_conditions.items():
                existing_conditions[condition] = existing_conditions.get(condition, 0) + count
            
            health_profile.detected_conditions = json.dumps(existing_conditions)
            health_profile.save()
        
        return health_profile
    except Exception as e:
        print(f"Error updating health profile: {e}")
        return None


def get_user_health_context(user_id):
    """Get user's health conditions for personalized responses"""
    try:
        health_profile = UserHealthProfile.objects.get(user_id=user_id)
        conditions = json.loads(health_profile.detected_conditions)
        
        if conditions:
            # Sort by frequency (highest first)
            sorted_conditions = sorted(conditions.items(), key=lambda x: x[1], reverse=True)
            return {cond: count for cond, count in sorted_conditions[:5]}  # Top 5
        return {}
    except UserHealthProfile.DoesNotExist:
        return {}
    except Exception as e:
        print(f"Error getting health context: {e}")
        return {}


def generate_personalized_recommendations(user_id, user_conditions):
    """Generate personalized health recommendations based on detected conditions"""
    if not user_conditions:
        return
    
    try:
        recommendations_map = {
            'diabetes': [
                {
                    'type': 'nutrition',
                    'title': 'Manage Blood Sugar Through Diet',
                    'description': 'Monitor carbohydrate intake, choose complex carbs, and maintain consistent meal times. Avoid sugary drinks and processed foods.',
                    'priority': 'high'
                },
                {
                    'type': 'exercise',
                    'title': 'Regular Exercise Routine',
                    'description': 'Aim for at least 150 minutes of moderate-intensity aerobic activity per week. Include resistance training 2-3 times weekly.',
                    'priority': 'high'
                }
            ],
            'hypertension': [
                {
                    'type': 'lifestyle',
                    'title': 'Reduce Sodium Intake',
                    'description': 'Keep daily sodium intake below 2,300mg. Avoid processed foods and use herbs for flavoring.',
                    'priority': 'high'
                },
                {
                    'type': 'exercise',
                    'title': 'Regular Cardiovascular Exercise',
                    'description': '30 minutes of moderate aerobic activity most days of the week helps lower blood pressure naturally.',
                    'priority': 'high'
                }
            ],
            'heart_disease': [
                {
                    'type': 'medical',
                    'title': 'Regular Cardiac Checkups',
                    'description': 'Schedule regular heart checkups with your cardiologist and monitor your cholesterol levels.',
                    'priority': 'high'
                },
                {
                    'type': 'nutrition',
                    'title': 'Heart-Healthy Diet',
                    'description': 'Follow Mediterranean diet with fruits, vegetables, whole grains, and healthy fats like olive oil.',
                    'priority': 'high'
                }
            ],
            'obesity': [
                {
                    'type': 'nutrition',
                    'title': 'Balanced Weight Management Diet',
                    'description': 'Focus on calorie deficit, increase protein intake for satiety, and eat more whole foods.',
                    'priority': 'high'
                },
                {
                    'type': 'exercise',
                    'title': 'Comprehensive Fitness Program',
                    'description': 'Combine cardio, strength training, and flexibility exercises. Start with 30 mins daily and gradually increase.',
                    'priority': 'high'
                }
            ],
            'asthma': [
                {
                    'type': 'medical',
                    'title': 'Asthma Action Plan',
                    'description': 'Work with your doctor to develop an asthma action plan. Keep rescue inhaler always available.',
                    'priority': 'high'
                },
                {
                    'type': 'lifestyle',
                    'title': 'Avoid Asthma Triggers',
                    'description': 'Identify and avoid triggers like allergens, air pollution, exercise in cold air, and strong odors.',
                    'priority': 'high'
                }
            ],
            'anxiety': [
                {
                    'type': 'lifestyle',
                    'title': 'Mindfulness and Meditation',
                    'description': 'Practice daily meditation and mindfulness exercises. Apps like Calm or Headspace can help.',
                    'priority': 'high'
                },
                {
                    'type': 'medical',
                    'title': 'Consider Professional Support',
                    'description': 'Consult a therapist or counselor. Cognitive Behavioral Therapy (CBT) is highly effective for anxiety.',
                    'priority': 'high'
                }
            ],
            'insomnia': [
                {
                    'type': 'lifestyle',
                    'title': 'Sleep Hygiene Practices',
                    'description': 'Maintain consistent sleep schedule, avoid screens 1 hour before bed, keep room dark and cool.',
                    'priority': 'high'
                },
                {
                    'type': 'medical',
                    'title': 'Consult Sleep Specialist',
                    'description': 'If insomnia persists beyond 2 weeks, consult a sleep specialist for proper diagnosis.',
                    'priority': 'medium'
                }
            ],
        }
        
        # Get top condition
        top_condition = list(user_conditions.keys())[0]
        
        if top_condition in recommendations_map:
            recommendations = recommendations_map[top_condition]
            
            # Check if recommendations already exist for this user
            existing_recs = PersonalizedRecommendation.objects.filter(
                user_id=user_id,
                recommendation_type=recommendations[0]['type'],
                title=recommendations[0]['title']
            ).exists()
            
            if not existing_recs:
                for rec in recommendations:
                    PersonalizedRecommendation.objects.create(
                        user_id=user_id,
                        recommendation_type=rec['type'],
                        title=rec['title'],
                        description=rec['description'],
                        priority=rec['priority']
                    )
    except Exception as e:
        print(f"Error generating recommendations: {e}")


# -------- End of Helper Functions --------


# -------- Rating Calculation Functions --------
def get_medical_bot_rating():
    """Get average rating for medical bot from feedback"""
    try:
        medical_feedbacks = FeedbackModel.objects.filter(feedback_type='medical')
        if medical_feedbacks.exists():
            avg_rating = medical_feedbacks.aggregate(models.Avg('rating'))['rating__avg']
            count = medical_feedbacks.count()
            return round(avg_rating, 1) if avg_rating else 0, count
        return 0, 0
    except Exception as e:
        print(f"Error calculating medical bot rating: {e}")
        return 0, 0


def get_nutrition_bot_rating():
    """Get average rating for nutrition bot from feedback"""
    try:
        nutrition_feedbacks = FeedbackModel.objects.filter(feedback_type='nutrition')
        if nutrition_feedbacks.exists():
            avg_rating = nutrition_feedbacks.aggregate(models.Avg('rating'))['rating__avg']
            count = nutrition_feedbacks.count()
            return round(avg_rating, 1) if avg_rating else 0, count
        return 0, 0
    except Exception as e:
        print(f"Error calculating nutrition bot rating: {e}")
        return 0, 0


def get_overall_rating():
    """Get overall rating for entire web application"""
    try:
        all_feedbacks = FeedbackModel.objects.exclude(feedback_type='general')
        if all_feedbacks.exists():
            avg_rating = all_feedbacks.aggregate(models.Avg('rating'))['rating__avg']
            count = all_feedbacks.count()
            return round(avg_rating, 1) if avg_rating else 0, count
        return 0, 0
    except Exception as e:
        print(f"Error calculating overall rating: {e}")
        return 0, 0


def get_rating_stats():
    """Get all rating statistics"""
    medical_rating, medical_count = get_medical_bot_rating()
    nutrition_rating, nutrition_count = get_nutrition_bot_rating()
    overall_rating, overall_count = get_overall_rating()
    
    return {
        'medical_rating': medical_rating,
        'medical_count': medical_count,
        'nutrition_rating': nutrition_rating,
        'nutrition_count': nutrition_count,
        'overall_rating': overall_rating,
        'overall_count': overall_count,
    }


# -------- End of Rating Functions --------



# ---------------- Base ----------------
def base(request):
    return render(request, 'base.html')


# ---------------- Register ----------------
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                # Hash the password before saving
                user.password = hash_password(form.cleaned_data['password'])
                user.save()
                messages.success(request, '✅ Registered successfully')
                return render(request, 'UserRegistration.html')
            except Exception as e:
                messages.error(request, f'❌ Registration error: {str(e)}')
        else:
            messages.error(request, '❌ Email/Mobile already exists')
    else:
        form = UserRegistrationForm()
    return render(request, 'UserRegistration.html', {'form': form})


# ---------------- Login ----------------
def UserLoginCheck(request):
    if request.method == "POST":
        loginid = request.POST.get('loginid')
        pswd = request.POST.get('password')
        try:
            user = UserRegistrationModel.objects.get(loginid=loginid)
            
            # Backward compatibility: Check both bcrypt and plain-text passwords
            password_valid = False
            
            # Try bcrypt verification first (for new passwords)
            if user.password.startswith('$2b$'):  # bcrypt hash marker
                password_valid = verify_password(pswd, user.password)
            else:
                # Legacy plain-text password support
                if user.password == pswd:
                    password_valid = True
                    # Auto-migrate plain-text password to bcrypt
                    user.password = hash_password(pswd)
                    user.save()
            
            if password_valid:
                if user.status == "activated":
                    request.session['id'] = user.id
                    request.session['loggeduser'] = user.name
                    return redirect('UserHome')
                else:
                    messages.error(request, '⚠️ Account not activated')
            else:
                messages.error(request, '❌ Invalid Login/Password')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, '❌ Invalid Login/Password')
    return render(request, 'UserLogin.html')


# ---------------- User Home ----------------
def UserHome(request):
    return render(request, 'users/UserHome.html')


# ---------------- Medical Chatbot ----------------
@rate_limit(max_calls=10, time_window=60)
def medical_chatbot(request):
    user_query = response_text = reasoning = None
    chat_history = []
    recommendations = []
    user_health_context = {}

    if request.method == "POST":
        user_query = request.POST.get("user_query", "").strip()
        if not user_query:
            messages.error(request, "❌ Please enter a medical query.")
        elif len(user_query) > 500:
            messages.error(request, "❌ Query is too long. Maximum 500 characters.")
        else:
            try:
                if not GEMINI_API_KEY:
                    messages.error(request, "⚠️ API is not configured. Please contact administrator.")
                else:
                    # Update health profile if user is logged in
                    if 'id' in request.session:
                        update_user_health_profile(request.session['id'], user_query)
                        user_health_context = get_user_health_context(request.session['id'])
                    
                    # Build personalized prompt with health context
                    health_context_text = ""
                    if user_health_context:
                        conditions_list = ", ".join([cond.replace('_', ' ').title() for cond in user_health_context.keys()])
                        health_context_text = f"\n\nIMPORTANT: The user has mentioned having: {conditions_list}. Please consider this in your advice."
                    
                    # RAG: retrieve relevant knowledge base chunks (if any)
                    rag_context, _ = get_rag_context_for_query(user_query, top_k=5)
                    rag_section = ""
                    if rag_context:
                        rag_section = f"""
Use the following trusted reference excerpts when answering. Prefer information from these excerpts when relevant; otherwise use your medical knowledge.

REFERENCE EXCERPTS:
{rag_context}

"""
                    
                    prompt = f"""
You are a **medical assistant chatbot** with personalized awareness of the user's health conditions.
Answer the user's query clearly, based on trusted medical knowledge.{rag_section}

DISCLAIMER: This is for informational purposes only and not a substitute for professional medical advice.{health_context_text}

Query: {user_query}

Respond in this format:
Advice: <main advice or explanation, tailored to their condition if applicable>
Reasoning: <short reasoning in 2-3 lines>
                    """
                    model = genai.GenerativeModel("models/gemini-2.5-flash")
                    response = model.generate_content(prompt)
                    
                    if not response or not response.text:
                        messages.error(request, "⚠️ No response from AI. Please try again.")
                    else:
                        raw_text = response.text.strip()
                        advice_match = re.search(r"Advice\s*:\s*(.*)", raw_text, re.IGNORECASE)
                        reason_match = re.search(r"Reasoning\s*:\s*(.*)", raw_text, re.IGNORECASE | re.DOTALL)

                        response_text = advice_match.group(1) if advice_match else raw_text
                        reasoning = reason_match.group(1) if reason_match else "No reasoning provided."
                        
                        # Save chat history
                        if 'id' in request.session:
                            try:
                                MedicalChatHistory.objects.create(
                                    user_id=request.session['id'],
                                    query=user_query,
                                    response=response_text,
                                    reasoning=reasoning
                                )
                                # Generate personalized recommendations based on detected conditions
                                if user_health_context:
                                    generate_personalized_recommendations(request.session['id'], user_health_context)
                            except Exception as e:
                                print(f"Error saving chat history: {e}")
                        
                        messages.success(request, "✅ Response generated successfully.")
                
            except TimeoutError:
                messages.error(request, "⏱️ Request timeout. The AI took too long to respond. Please try again.")
                response_text = None
            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Unauthorized" in error_msg:
                    messages.error(request, "⚠️ API authentication failed. Please check configuration.")
                elif "429" in error_msg or "quota" in error_msg:
                    messages.error(request, "⚠️ Rate limit exceeded. Please try again later.")
                else:
                    messages.error(request, f"❌ Error: {error_msg[:100]}")
                response_text = None

    # Load chat history for logged-in users (always loaded)
    if 'id' in request.session:
        try:
            chat_history = MedicalChatHistory.objects.filter(user_id=request.session['id'])[:10]
            recommendations = PersonalizedRecommendation.objects.filter(user_id=request.session['id'], is_read=False)[:5]
            user_health_context = get_user_health_context(request.session['id'])
        except Exception as e:
            print(f"Error loading history: {e}")

    # Get ratings
    rating_stats = get_rating_stats()

    return render(request, "users/medical_chatbot.html", {
        "user_query": user_query,
        "response_text": response_text,
        "reasoning": reasoning,
        "chat_history": chat_history,
        "recommendations": recommendations,
        "health_conditions": user_health_context,
        "medical_rating": rating_stats['medical_rating'],
        "medical_count": rating_stats['medical_count'],
        "overall_rating": rating_stats['overall_rating'],
        "overall_count": rating_stats['overall_count'],
    })


# ---------------- Nutrition Bot ----------------
@rate_limit(max_calls=5, time_window=60)
def nutrition_bot(request):
    nutrition_result = None
    health_percentage = None
    calories_info = None
    nutrition_history = []
    
    if request.method == "POST" and request.FILES.get("food_image"):
        image_file = request.FILES["food_image"]

        # Validate file size (max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            messages.error(request, "❌ Image file is too large. Maximum size is 10MB.")
        else:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/webp', 'image/gif']
            mime_type, _ = mimetypes.guess_type(image_file.name)
            if mime_type and mime_type not in allowed_types:
                messages.error(request, "❌ Invalid image format. Please upload JPEG, PNG, WebP, or GIF.")
            else:
                try:
                    if not GEMINI_API_KEY:
                        messages.error(request, "⚠️ API is not configured. Please contact administrator.")
                    else:
                        prompt = """
You are a nutrition expert and health analyst. 
Analyze the uploaded food image and return the information in EXACTLY this format:

=== FOOD ANALYSIS ===
Ingredients Detected: [list the ingredients you can see]

Calories: [provide approximate calories per serving]

Nutritional Breakdown:
- Carbohydrates: [percentage/amount]
- Protein: [percentage/amount]
- Fat: [percentage/amount]
- Fiber: [grams/amount]
- Sugar: [grams/amount]

Health Score: [0-100 percentage, where 100 is extremely healthy]

Health Assessment: [One of: Very Healthy, Healthy, Moderate, Unhealthy, Very Unhealthy]

Health Suggestion: [2-3 sentences explaining why and any recommendations]

===END===
"""

                        # Convert Django InMemoryUploadedFile -> Gemini-compatible format
                        mime_type = mime_type or "image/png"
                        image_data = {
                            "mime_type": mime_type,
                            "data": image_file.read()
                        }

                        model = genai.GenerativeModel("models/gemini-2.5-flash")
                        response = model.generate_content([prompt, image_data])
                        
                        if not response or not response.text:
                            messages.error(request, "⚠️ No response from AI. Please try again.")
                        else:
                            raw_response = response.text.strip()
                            
                            # Parse the structured response
                            nutrition_result = raw_response
                            
                            # Extract health percentage
                            health_match = re.search(r"Health Score\s*:\s*(\d+)", raw_response, re.IGNORECASE)
                            if health_match:
                                health_percentage = int(health_match.group(1))
                            
                            # Extract calories
                            calories_match = re.search(r"Calories\s*:\s*([^\n]+)", raw_response, re.IGNORECASE)
                            if calories_match:
                                calories_info = calories_match.group(1).strip()
                            
                            # Save nutrition analysis to history
                            if 'id' in request.session:
                                try:
                                    NutritionAnalysisHistory.objects.create(
                                        user_id=request.session['id'],
                                        analysis_result=nutrition_result,
                                        health_percentage=health_percentage,
                                        calories_info=calories_info
                                    )
                                except Exception as e:
                                    print(f"Error saving nutrition history: {e}")
                            
                            messages.success(request, "✅ Nutrition analysis completed successfully.")

                except TimeoutError:
                    messages.error(request, "⏱️ Image analysis timeout. The AI took too long to respond. Please try again.")
                    nutrition_result = None
                except Exception as e:
                    error_msg = str(e)
                    if "401" in error_msg or "Unauthorized" in error_msg:
                        messages.error(request, "⚠️ API authentication failed. Please check configuration.")
                    elif "429" in error_msg or "quota" in error_msg:
                        messages.error(request, "⚠️ Rate limit exceeded. Please try again later.")
                    elif "invalid_argument" in error_msg.lower() or "unsupported" in error_msg.lower():
                        messages.error(request, "❌ Could not analyze the image. Please try a different food image.")
                    else:
                        messages.error(request, f"❌ Error: {error_msg[:100]}")
                    nutrition_result = None

    # Load analysis history for logged-in users

    if 'id' in request.session:
        try:
            nutrition_history = NutritionAnalysisHistory.objects.filter(user_id=request.session['id'])[:10]
        except Exception as e:
            print(f"Error loading nutrition history: {e}")

    # Get ratings
    rating_stats = get_rating_stats()

    return render(request, "users/nutrition_bot.html", {
        "nutrition_result": nutrition_result,
        "health_percentage": health_percentage,
        "calories_info": calories_info,
        "nutrition_history": nutrition_history,
        "nutrition_rating": rating_stats['nutrition_rating'],
        "nutrition_count": rating_stats['nutrition_count'],
        "overall_rating": rating_stats['overall_rating'],
        "overall_count": rating_stats['overall_count'],
    })


# ---------------- Feedback ----------------
@rate_limit(max_calls=5, time_window=60)
def feedback_view(request):
    if 'id' not in request.session:
        messages.error(request, "❌ Please login first")
        return redirect('UserLogin')
    
    if request.method == "POST":
        form = FeedbackForm(request.POST)
        if form.is_valid():
            try:
                feedback = form.save(commit=False)
                feedback.user_id = request.session['id']
                
                # Validate feedback content length
                if len(form.cleaned_data.get('message', '')) > 1000:
                    messages.error(request, '❌ Feedback message exceeds maximum length')
                else:
                    feedback.save()
                    messages.success(request, '✅ Thank you for your feedback!')
                    return redirect('feedback')
            except Exception as e:
                messages.error(request, f'❌ Error submitting feedback: {str(e)[:100]}')
        else:
            messages.error(request, '❌ Please fill in all required fields correctly')
    else:
        form = FeedbackForm()
    
    # Get user's previous feedback
    try:
        user_feedbacks = FeedbackModel.objects.filter(user_id=request.session['id']).order_by('-created_at')
    except Exception as e:
        messages.warning(request, '⚠️ Could not load feedback history')
        user_feedbacks = []
    
    # Get ratings
    rating_stats = get_rating_stats()

    return render(request, 'users/feedback.html', {
        'form': form,
        'user_feedbacks': user_feedbacks,
        'medical_rating': rating_stats['medical_rating'],
        'medical_count': rating_stats['medical_count'],
        'nutrition_rating': rating_stats['nutrition_rating'],
        'nutrition_count': rating_stats['nutrition_count'],
        'overall_rating': rating_stats['overall_rating'],
        'overall_count': rating_stats['overall_count'],
    })

# ----------------Personalized Insights Dashboard ----------------
def insights_dashboard(request):
    """Display personalized health insights and analytics"""
    if 'id' not in request.session:
        return redirect('UserLogin')
    
    user_id = request.session['id']
    insights_data = {}
    
    try:
        # Get or create health insight record
        health_insight, created = HealthInsight.objects.get_or_create(user_id=user_id)
        
        # Get chat and nutrition history
        chat_history = MedicalChatHistory.objects.filter(user_id=user_id)
        nutrition_history = NutritionAnalysisHistory.objects.filter(user_id=user_id)
        recommendations = PersonalizedRecommendation.objects.filter(user_id=user_id)
        
        # Calculate metrics
        total_queries = chat_history.count()
        total_analyses = nutrition_history.count()
        
        # Calculate average nutrition score
        avg_nutrition = 0
        if nutrition_history.exists():
            scores = [n.health_percentage for n in nutrition_history if n.health_percentage]
            avg_nutrition = sum(scores) // len(scores) if scores else 0
        
        # Extract health concerns from chat queries
        health_concerns = {}
        keywords = {
            'diabetes': ['diabetes', 'blood sugar', 'glucose'],
            'heart': ['heart', 'cardiac', 'cholesterol', 'blood pressure'],
            'weight': ['weight', 'obesity', 'overweight', 'diet'],
            'sleep': ['sleep', 'insomnia', 'insomnia'],
            'stress': ['stress', 'anxiety', 'mental'],
            'digestion': ['digestion', 'stomach', 'gut', 'ibs'],
            'allergy': ['allergy', 'allergic', 'allergen'],
        }
        
        for chat in chat_history:
            query_lower = chat.query.lower()
            for concern, keywords_list in keywords.items():
                if any(kw in query_lower for kw in keywords_list):
                    health_concerns[concern] = health_concerns.get(concern, 0) + 1
        
        # Calculate overall health score (0-100)
        # Formula: Base 50 + nutrition score factor + query frequency factor - concerns factor
        health_score = 50
        if avg_nutrition > 0:
            health_score += (avg_nutrition - 50) // 2
        
        query_factor = min(20, total_queries * 2)  # Max +20 for queries
        health_score += query_factor
        
        concerns_penalty = min(15, len(health_concerns) * 3)
        health_score -= concerns_penalty
        
        health_score = max(0, min(100, health_score))
        
        # Calculate activity streak
        if chat_history.exists() or nutrition_history.exists():
            last_activity = max(
                chat_history.latest('created_at').created_at if chat_history.exists() else datetime.min,
                nutrition_history.latest('created_at').created_at if nutrition_history.exists() else datetime.min
            )
            days_since = (datetime.now(last_activity.tzinfo) - last_activity).days
            activity_streak = max(0, 7 - days_since)  # Max 7 day streak
        else:
            activity_streak = 0
        
        # Update health insight record
        health_insight.overall_health_score = health_score
        health_insight.total_queries = total_queries
        health_insight.total_nutrition_analyses = total_analyses
        health_insight.avg_nutrition_score = avg_nutrition
        health_insight.top_health_concerns = json.dumps(health_concerns)
        health_insight.activity_streak = activity_streak
        health_insight.save()
        
        # Prepare data for template
        insights_data = {
            'health_score': health_score,
            'total_queries': total_queries,
            'total_analyses': total_analyses,
            'avg_nutrition_score': avg_nutrition,
            'health_concerns': health_concerns,
            'activity_streak': activity_streak,
            'recent_chats': chat_history[:5],
            'recent_analyses': nutrition_history[:5],
            'recommendations': recommendations[:5],
        }
        
        # Generate health status text
        if health_score >= 80:
            insights_data['health_status'] = '🌟 Excellent'
            insights_data['status_color'] = '#10b981'
        elif health_score >= 60:
            insights_data['health_status'] = '✅ Good'
            insights_data['status_color'] = '#3b82f6'
        elif health_score >= 40:
            insights_data['health_status'] = '⚠️ Fair'
            insights_data['status_color'] = '#f59e0b'
        else:
            insights_data['health_status'] = '❌ Needs Attention'
            insights_data['status_color'] = '#ef4444'
        
    except Exception as e:
        print(f"Error loading insights: {e}")
        messages.error(request, "Error loading insights")
    
    return render(request, 'users/insights_dashboard.html', insights_data)

# ----------------Delete Medical Chat History ----------------
@require_http_methods(["DELETE"])
def delete_medical_history(request, chat_id):
    """Delete a specific medical chat history entry"""
    try:
        if 'id' not in request.session:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        # Get the chat history entry and verify ownership
        chat = MedicalChatHistory.objects.get(id=chat_id, user_id=request.session['id'])
        chat.delete()
        
        return JsonResponse({'success': True, 'message': 'Chat history deleted successfully'})
    except MedicalChatHistory.DoesNotExist:
        return JsonResponse({'error': 'Chat history not found'}, status=404)
    except Exception as e:
        print(f"Error deleting chat history: {e}")
        return JsonResponse({'error': 'Error deleting chat history'}, status=500)


# ----------------Delete Nutrition History ----------------
@require_http_methods(["DELETE"])
def delete_nutrition_history(request, history_id):
    """Delete a specific nutrition analysis history entry"""
    try:
        if 'id' not in request.session:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        # Get the nutrition history entry and verify ownership
        history = NutritionAnalysisHistory.objects.get(id=history_id, user_id=request.session['id'])
        history.delete()
        
        return JsonResponse({'success': True, 'message': 'Nutrition history deleted successfully'})
    except NutritionAnalysisHistory.DoesNotExist:
        return JsonResponse({'error': 'Nutrition history not found'}, status=404)
    except Exception as e:
        print(f"Error deleting nutrition history: {e}")
        return JsonResponse({'error': 'Error deleting nutrition history'}, status=500)