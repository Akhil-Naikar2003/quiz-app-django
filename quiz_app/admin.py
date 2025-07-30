from django.contrib import admin
from .models import (
    Category, Quiz, Question, Choice, QuizAttempt, UserAnswer, QuizAnalytics, UserProfile
)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'quiz_count', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    
    def quiz_count(self, obj):
        return obj.quizzes.count()
    quiz_count.short_description = 'Quizzes'

class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ('text', 'is_correct', 'order')

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True
    fields = ('text', 'question_type', 'points', 'order')

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'creator', 'difficulty', 'status', 'question_count', 'total_attempts', 'average_score', 'created_at')
    list_filter = ('difficulty', 'status', 'category', 'created_at', 'pdf_processed')
    search_fields = ('title', 'description', 'creator__username', 'category__name')
    readonly_fields = ('id', 'slug', 'total_attempts', 'average_score', 'created_at', 'updated_at', 'published_at')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [QuestionInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'description', 'category', 'difficulty', 'status')
        }),
        ('Configuration', {
            'fields': ('time_limit', 'passing_score', 'max_attempts')
        }),
        ('File Management', {
            'fields': ('pdf_file', 'pdf_processed')
        }),
        ('Statistics', {
            'fields': ('total_attempts', 'average_score'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        })
    )
    
    def question_count(self, obj):
        return obj.question_count
    question_count.short_description = 'Questions'

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'quiz', 'question_type', 'points', 'order', 'choices_count')
    list_filter = ('question_type', 'quiz__difficulty', 'quiz__status', 'created_at')
    search_fields = ('text', 'quiz__title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [ChoiceInline]
    
    fieldsets = (
        ('Question Details', {
            'fields': ('quiz', 'text', 'question_type', 'points', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def text_preview(self, obj):
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    text_preview.short_description = 'Question Text'
    
    def choices_count(self, obj):
        return obj.choices.count()
    choices_count.short_description = 'Choices'

@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ('text_preview', 'question', 'is_correct', 'order')
    list_filter = ('is_correct', 'question__question_type', 'question__quiz__difficulty')
    search_fields = ('text', 'question__text', 'question__quiz__title')
    readonly_fields = ('id', 'created_at')
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Choice Text'

@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'quiz', 'attempt_number', 'status', 'score', 'percentage', 'passed', 'time_taken', 'started_at')
    list_filter = ('status', 'passed', 'quiz__difficulty', 'started_at')
    search_fields = ('user__username', 'quiz__title')
    readonly_fields = ('id', 'percentage', 'passed', 'started_at', 'completed_at')
    
    fieldsets = (
        ('Attempt Information', {
            'fields': ('user', 'quiz', 'attempt_number', 'status')
        }),
        ('Results', {
            'fields': ('score', 'percentage', 'correct_answers', 'total_questions', 'passed')
        }),
        ('Timing', {
            'fields': ('time_taken', 'started_at', 'completed_at')
        })
    )

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('user', 'question_preview', 'selected_choice_preview', 'is_correct', 'points_earned', 'time_taken', 'answered_at')
    list_filter = ('is_correct', 'question__question_type', 'answered_at')
    search_fields = ('attempt__user__username', 'question__text', 'selected_choice__text')
    readonly_fields = ('id', 'is_correct', 'points_earned', 'answered_at')
    
    def user(self, obj):
        return obj.attempt.user
    user.short_description = 'User'
    
    def question_preview(self, obj):
        return obj.question.text[:50] + '...' if len(obj.question.text) > 50 else obj.question.text
    question_preview.short_description = 'Question'
    
    def selected_choice_preview(self, obj):
        if obj.selected_choice:
            return obj.selected_choice.text[:30] + '...' if len(obj.selected_choice.text) > 30 else obj.selected_choice.text
        return obj.text_answer[:30] + '...' if obj.text_answer else 'No answer'
    selected_choice_preview.short_description = 'Answer'

@admin.register(QuizAnalytics)
class QuizAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('quiz', 'total_attempts', 'successful_attempts', 'success_rate', 'average_score', 'accuracy_rate', 'last_updated')
    readonly_fields = ('quiz', 'total_attempts', 'successful_attempts', 'average_score', 'average_time', 'total_questions_answered', 'correct_answers', 'success_rate', 'accuracy_rate', 'last_updated')
    
    def success_rate(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate.short_description = 'Success Rate'
    
    def accuracy_rate(self, obj):
        return f"{obj.accuracy_rate:.1f}%"
    accuracy_rate.short_description = 'Accuracy Rate'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'points', 'badges_count', 'created_at')
    list_filter = ('points',)
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('user',)
    
    def badges_count(self, obj):
        return len(obj.badges) if obj.badges else 0
    badges_count.short_description = 'Badges'
    
    def created_at(self, obj):
        return obj.user.date_joined
    created_at.short_description = 'Joined'
