from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from users.forms import UserRegistrationForm
from .models import UserRegistrationModel
import os, re, mimetypes
import google.generativeai as genai

# ---------------- Gemini Config ----------------
GEMINI_API_KEY = getattr(settings, "GEMINI_API_KEY", None) or \
                 os.getenv("GEMINI_API_KEY") or \
                 "AIzaSyAysVqWZ-Ydq8NTcPZN6QwpVX5JkEDE17Q"
genai.configure(api_key=GEMINI_API_KEY)


# ---------------- Base ----------------
def base(request):
    return render(request, 'base.html')


# ---------------- Register ----------------
def UserRegisterActions(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '✅ Registered successfully')
            return render(request, 'UserRegistration.html')
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
            user = UserRegistrationModel.objects.get(loginid=loginid, password=pswd)
            if user.status == "activated":
                request.session['id'] = user.id
                request.session['loggeduser'] = user.name
                return redirect('UserHome')
            else:
                messages.error(request, '⚠️ Account not activated')
        except UserRegistrationModel.DoesNotExist:
            messages.error(request, '❌ Invalid Login/Password')
    return render(request, 'UserLogin.html')


# ---------------- User Home ----------------
def UserHome(request):
    return render(request, 'users/UserHome.html')


# ---------------- Medical Chatbot ----------------
def medical_chatbot(request):
    user_query = response_text = reasoning = None

    if request.method == "POST":
        user_query = request.POST.get("user_query", "").strip()
        if not user_query:
            messages.error(request, "Please enter a medical query.")
        else:
            try:
                prompt = f"""
You are a **medical assistant chatbot**.
Answer the user's query clearly, based on trusted medical knowledge.

Query: {user_query}

Respond in this format:
Advice: <main advice or explanation>
Reasoning: <short reasoning in 2-3 lines>
                """
                model = genai.GenerativeModel("models/gemini-2.5-flash")
                response = model.generate_content(prompt)
                raw_text = response.text.strip()
                advice_match = re.search(r"Advice\s*:\s*(.*)", raw_text, re.IGNORECASE)
                reason_match = re.search(r"Reasoning\s*:\s*(.*)", raw_text, re.IGNORECASE | re.DOTALL)

                response_text = advice_match.group(1) if advice_match else raw_text
                reasoning = reason_match.group(1) if reason_match else "No reasoning provided."
            except Exception as e:
                response_text = f" Error: {str(e)}"

    return render(request, "users/medical_chatbot.html", {
        "user_query": user_query,
        "response_text": response_text,
        "reasoning": reasoning
    })


# ---------------- Nutrition Bot ----------------
def nutrition_bot(request):
    nutrition_result = None
    if request.method == "POST" and request.FILES.get("food_image"):
        image_file = request.FILES["food_image"]

        try:
            prompt = """
You are a nutrition expert. 
Analyze the uploaded food image and return:

- Ingredients detected
- Calories (approximate)
- Nutritional Breakdown (Carbs, Protein, Fat, Fiber, Sugar)
- Health Suggestion (Healthy / Unhealthy and why)
"""

            # Convert Django InMemoryUploadedFile -> Gemini-compatible format
            mime_type, _ = mimetypes.guess_type(image_file.name)
            image_data = {
                "mime_type": mime_type or "image/png",
                "data": image_file.read()
            }

            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content([prompt, image_data])
            nutrition_result = response.text.strip()

        except Exception as e:
            nutrition_result = f" Error: {str(e)}"

    return render(request, "users/nutrition_bot.html", {
        "nutrition_result": nutrition_result
    })
