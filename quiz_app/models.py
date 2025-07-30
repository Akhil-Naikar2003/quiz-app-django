from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver

class Category(models.Model):
    """
    Quiz categories for better organization
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Quiz(models.Model):
    """
    Main quiz model with improved design and constraints
    """
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    description = models.TextField(blank=True)
    
    # Classification
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium', db_index=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', db_index=True)
    
    # Configuration
    time_limit = models.PositiveIntegerField(default=0, help_text="Time limit in minutes (0 = no limit)")
    passing_score = models.PositiveIntegerField(default=60, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_attempts = models.PositiveIntegerField(default=3, help_text="Maximum attempts allowed (0 = unlimited)")
    
    # File handling
    pdf_file = models.FileField(upload_to='quiz_pdfs/%Y/%m/%d/', null=True, blank=True)
    pdf_processed = models.BooleanField(default=False)
    
    # Metadata
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    total_attempts = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'difficulty']),
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['category', 'status']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = f"{self.title.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def question_count(self):
        return self.questions.count()
    
    @property
    def is_active(self):
        return self.status == 'published'
    
    def can_user_attempt(self, user):
        """Check if user can take another attempt at this quiz"""
        if self.max_attempts == 0:  # Unlimited attempts
            return True
        
        current_attempts = self.attempts.filter(user=user).count()
        return current_attempts < self.max_attempts
    
    def get_user_attempt_count(self, user):
        """Get the number of attempts a user has made for this quiz"""
        return self.attempts.filter(user=user).count()

    def has_vector_store(self):
        """Check if this quiz has a vector store available"""
        if not self.pdf_file:
            return False
        
        from django.conf import settings
        import os
        vector_store_path = os.path.join(settings.MEDIA_ROOT, 'vector_stores', f'quiz_{self.id}')
        return os.path.exists(vector_store_path)

class Question(models.Model):
    """
    Question model with improved structure and validation
    """
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('fill_blank', 'Fill in the Blank'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='multiple_choice')
    points = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])
    order = models.PositiveIntegerField(default=0, help_text="Question order in the quiz")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['quiz', 'order']
        indexes = [
            models.Index(fields=['quiz', 'order']),
        ]
    
    def __str__(self):
        return f"{self.quiz.title} - Question {self.order}"
    
    def clean(self):
        if self.question_type == 'multiple_choice' and self.choices.count() < 2:
            raise ValidationError("Multiple choice questions must have at least 2 choices.")
        if self.question_type == 'true_false' and self.choices.count() != 2:
            raise ValidationError("True/False questions must have exactly 2 choices.")
    
    @property
    def correct_choice(self):
        return self.choices.filter(is_correct=True).first()

class Choice(models.Model):
    """
    Choice model for multiple choice and true/false questions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        unique_together = ['question', 'order']
        indexes = [
            models.Index(fields=['question', 'is_correct']),
        ]
    
    def __str__(self):
        return f"{self.question.text[:50]} - {self.text[:30]}"
    
    def clean(self):
        # Ensure only one correct choice per question
        if self.is_correct:
            other_correct = Choice.objects.filter(question=self.question, is_correct=True)
            if self.pk:
                other_correct = other_correct.exclude(pk=self.pk)
            if other_correct.exists():
                raise ValidationError("Only one choice can be correct per question.")

class QuizAttempt(models.Model):
    """
    Quiz attempt model with comprehensive tracking
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
        ('timeout', 'Timed Out'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    
    # Attempt details
    attempt_number = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    
    # Timing
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_taken = models.PositiveIntegerField(default=0, help_text="Time taken in seconds")
    
    # Results
    correct_answers = models.PositiveIntegerField(default=0)
    total_questions = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-started_at']
        unique_together = ['user', 'quiz', 'attempt_number']
        indexes = [
            models.Index(fields=['user', 'quiz']),
            models.Index(fields=['status', 'started_at']),
            models.Index(fields=['quiz', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.quiz.title} (Attempt {self.attempt_number})"
    
    def save(self, *args, **kwargs):
        if self.total_questions > 0:
            self.percentage = (self.correct_answers / self.total_questions) * 100
            self.passed = self.percentage >= self.quiz.passing_score
        super().save(*args, **kwargs)
    
    @property
    def duration_minutes(self):
        return self.time_taken // 60 if self.time_taken else 0

class UserAnswer(models.Model):
    """
    User answer model with improved tracking
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE, null=True, blank=True)
    text_answer = models.TextField(blank=True, help_text="For fill-in-the-blank questions")
    
    # Answer details
    is_correct = models.BooleanField(default=False)
    points_earned = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    time_taken = models.PositiveIntegerField(default=0, help_text="Time taken to answer in seconds")
    
    # Metadata
    answered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['attempt', 'question']
        indexes = [
            models.Index(fields=['attempt', 'question']),
            models.Index(fields=['is_correct']),
        ]
    
    def __str__(self):
        return f"{self.attempt.user.username} - {self.question.text[:50]}"
    
    def save(self, *args, **kwargs):
        if self.selected_choice:
            self.is_correct = self.selected_choice.is_correct
            self.points_earned = self.question.points if self.is_correct else 0
        super().save(*args, **kwargs)

class QuizAnalytics(models.Model):
    """
    Analytics model for tracking quiz performance metrics
    """
    quiz = models.OneToOneField(Quiz, on_delete=models.CASCADE, related_name='analytics')
    
    # Performance metrics
    total_attempts = models.PositiveIntegerField(default=0)
    successful_attempts = models.PositiveIntegerField(default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    average_time = models.PositiveIntegerField(default=0, help_text="Average time in seconds")
    
    # Question analytics
    total_questions_answered = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Quiz Analytics"
    
    def __str__(self):
        return f"Analytics for {self.quiz.title}"
    
    @property
    def success_rate(self):
        return (self.successful_attempts / self.total_attempts * 100) if self.total_attempts > 0 else 0
    
    @property
    def accuracy_rate(self):
        return (self.correct_answers / self.total_questions_answered * 100) if self.total_questions_answered > 0 else 0

class ChatSession(models.Model):
    """
    Chat session model for AI teacher conversations
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='chat_sessions', null=True, blank=True)
    
    # Session details
    title = models.CharField(max_length=255, default="AI Teacher Chat")
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-last_message_at', '-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"
    
    @property
    def message_count(self):
        return self.messages.count()
    
    @property
    def last_message(self):
        return self.messages.order_by('-timestamp').first()

class ChatMessage(models.Model):
    """
    Individual chat message model
    """
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('assistant', 'AI Assistant'),
        ('system', 'System Message'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    
    # Message content
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='user')
    content = models.TextField()
    
    # Metadata
    timestamp = models.DateTimeField(auto_now_add=True)
    tokens_used = models.PositiveIntegerField(default=0, help_text="Number of tokens used in this message")
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.session.user.username} - {self.message_type} ({self.timestamp.strftime('%H:%M')})"
    
    @property
    def is_user_message(self):
        return self.message_type == 'user'
    
    @property
    def is_assistant_message(self):
        return self.message_type == 'assistant'

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    points = models.PositiveIntegerField(default=0)
    badges = models.JSONField(default=list, blank=True, help_text="List of badge names awarded to the user")
    
    def __str__(self):
        return f"Profile for {self.user.username}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

