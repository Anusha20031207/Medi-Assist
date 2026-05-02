from django.contrib import admin
from .models import UserRegistrationModel, MedicalChatHistory, NutritionAnalysisHistory, PersonalizedRecommendation, FeedbackModel, HealthInsight, UserHealthProfile

# Register your models here.

@admin.register(UserHealthProfile)
class UserHealthProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'last_updated')
    search_fields = ('user__name', 'user__loginid')
    readonly_fields = ('detected_conditions', 'allergies', 'medications', 'dietary_restrictions', 'created_at', 'last_updated')
    
    def has_add_permission(self, request):
        return False  # Auto-created, not manually added


@admin.register(PersonalizedRecommendation)
class PersonalizedRecommendationAdmin(admin.ModelAdmin):
    list_display = ('user', 'recommendation_type', 'title', 'priority', 'is_read', 'created_at')
    list_filter = ('recommendation_type', 'priority', 'is_read')
    search_fields = ('user__name', 'title')


@admin.register(MedicalChatHistory)
class MedicalChatHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'query', 'created_at')
    search_fields = ('user__name', 'query')
    readonly_fields = ('created_at',)


@admin.register(FeedbackModel)
class FeedbackModelAdmin(admin.ModelAdmin):
    list_display = ('user', 'subject', 'rating', 'created_at', 'status')
    list_filter = ('rating', 'status', 'created_at')
    search_fields = ('user__name', 'subject')
