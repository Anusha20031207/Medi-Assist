from django.db import models

# Create your models here.
from django.db import models
from .security import hash_password

# Create your models here.
class UserRegistrationModel(models.Model):
    name = models.CharField(max_length=100)
    loginid = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=255)  # Increased for bcrypt hash
    mobile = models.CharField(unique=True, max_length=100)
    email = models.CharField(unique=True, max_length=100)
    locality = models.CharField(max_length=100)
    address = models.CharField(max_length=1000)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    status = models.CharField(max_length=100)

    def __str__(self):
        return self.loginid

    class Meta:
        db_table = 'UserRegistrations'


class MedicalChatHistory(models.Model):
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    reasoning = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Chat by {self.user.name} on {self.created_at}"
    
    class Meta:
        db_table = 'MedicalChatHistory'
        ordering = ['-created_at']


class NutritionAnalysisHistory(models.Model):
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    food_image = models.ImageField(upload_to='nutrition_uploads/')
    analysis_result = models.TextField()
    health_percentage = models.IntegerField(null=True, blank=True)
    calories_info = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Nutrition analysis by {self.user.name} on {self.created_at}"
    
    class Meta:
        db_table = 'NutritionAnalysisHistory'
        ordering = ['-created_at']


class PersonalizedRecommendation(models.Model):
    RECOMMENDATION_TYPES = [
        ('medical', 'Medical Advice'),
        ('nutrition', 'Nutrition'),
        ('lifestyle', 'Lifestyle'),
        ('exercise', 'Exercise'),
    ]
    
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    priority = models.CharField(max_length=20, choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')], default='medium')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.recommendation_type} for {self.user.name}"
    
    class Meta:
        db_table = 'PersonalizedRecommendations'
        ordering = ['-created_at']


class FeedbackModel(models.Model):
    FEEDBACK_TYPES = [
        ('medical', 'Medical Bot'),
        ('nutrition', 'Nutrition Bot'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(UserRegistrationModel, on_delete=models.CASCADE)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES, default='general')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    rating = models.IntegerField(choices=[(1, '1 - Poor'), (2, '2 - Fair'), (3, '3 - Good'), (4, '4 - Very Good'), (5, '5 - Excellent')])
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='unread', choices=[('unread', 'Unread'), ('read', 'Read')])

    def __str__(self):
        return f"Feedback from {self.user.name} - {self.subject}"

    class Meta:
        db_table = 'UserFeedback'
        ordering = ['-created_at']


class UserHealthProfile(models.Model):
    """Store user's detected health conditions and medical history"""
    user = models.OneToOneField(UserRegistrationModel, on_delete=models.CASCADE, related_name='health_profile')
    detected_conditions = models.TextField(default='{}')  # JSON string of detected conditions with frequency
    allergies = models.TextField(default='[]')  # JSON list of detected allergies
    medications = models.TextField(default='[]')  # JSON list of mentioned medications
    dietary_restrictions = models.TextField(default='[]')  # JSON list of dietary needs
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Health Profile for {self.user.name}"
    
    class Meta:
        db_table = 'UserHealthProfiles'


class HealthInsight(models.Model):
    """Store calculated health metrics and insights for users"""
    user = models.OneToOneField(UserRegistrationModel, on_delete=models.CASCADE, related_name='health_insight')
    overall_health_score = models.IntegerField(default=50)  # 0-100
    total_queries = models.IntegerField(default=0)
    total_nutrition_analyses = models.IntegerField(default=0)
    avg_nutrition_score = models.IntegerField(default=0)  # 0-100
    top_health_concerns = models.TextField(default='')  # JSON string of concerns
    activity_streak = models.IntegerField(default=0)  # Days of consecutive usage
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Health Insight for {self.user.name}"
    
    class Meta:
        db_table = 'HealthInsights'


class DocumentChunk(models.Model):
    """
    Stores text chunks for RAG knowledge base.
    embedding_json: JSON array of floats from Gemini text-embedding-004.
    """
    source = models.CharField(max_length=500, help_text="e.g. filename or document title")
    text = models.TextField(help_text="Chunk text content")
    embedding_json = models.TextField(null=True, blank=True, help_text="JSON array of embedding floats")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'RAG_DocumentChunks'
        ordering = ['source', 'id']


# from django.db import models

# class TumorPrediction(models.Model):
#     patient_name = models.CharField(max_length=100)
#     uploaded_mri = models.ImageField(upload_to='uploads/mri/')
#     uploaded_pet = models.ImageField(upload_to='uploads/pet/')
#     fused_image = models.ImageField(upload_to='uploads/fused/', blank=True, null=True)
#     prediction_result = models.CharField(max_length=50, blank=True, null=True)
#     confidence_score = models.FloatField(blank=True, null=True)
#     created_at = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.patient_name} - {self.prediction_result or 'Pending'}"

