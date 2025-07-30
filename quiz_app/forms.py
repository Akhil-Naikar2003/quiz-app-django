from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Quiz, Question, Choice, ChatMessage, ChatSession
from django.conf import settings
import os

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

class QuizForm(forms.ModelForm):
    number_of_questions = forms.IntegerField(
        min_value=3,
        max_value=25,
        initial=10,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Quiz
        fields = ('title', 'difficulty', 'pdf_file', 'number_of_questions')
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'pdf_file': forms.FileInput(attrs={'class': 'form-control'}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3}),
        }

class ChoiceForm(forms.ModelForm):
    class Meta:
        model = Choice
        fields = ('text', 'is_correct')
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class QuizQuestionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        questions = kwargs.pop('questions', [])
        super(QuizQuestionForm, self).__init__(*args, **kwargs)
        
        for question in questions:
            choices = [(choice.id, choice.text) for choice in question.choices.all()]
            self.fields[f'question_{question.id}'] = forms.ChoiceField(
                label=question.text,
                choices=choices,
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
                required=True
            )

class OpenTDBQuizForm(forms.Form):
    QUIZ_TYPE_CHOICES = [
        ('pdf', 'Upload PDF'),
        ('api', 'Use OpenTDB API')
    ]
    
    CATEGORY_CHOICES = [
        (9, 'General Knowledge'),
        (10, 'Entertainment: Books'),
        (11, 'Entertainment: Film'),
        (12, 'Entertainment: Music'),
        (13, 'Entertainment: Musicals & Theatres'),
        (14, 'Entertainment: Television'),
        (15, 'Entertainment: Video Games'),
        (16, 'Entertainment: Board Games'),
        (17, 'Science & Nature'),
        (18, 'Science: Computers'),
        (19, 'Science: Mathematics'),
        (20, 'Mythology'),
        (21, 'Sports'),
        (22, 'Geography'),
        (23, 'History'),
        (24, 'Politics'),
        (25, 'Art'),
        (26, 'Celebrities'),
        (27, 'Animals'),
        (28, 'Vehicles'),
        (29, 'Entertainment: Comics'),
        (30, 'Science: Gadgets'),
        (31, 'Entertainment: Japanese Anime & Manga'),
        (32, 'Entertainment: Cartoon & Animations')
    ]
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard')
    ]
    
    quiz_type = forms.ChoiceField(
        choices=QUIZ_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='pdf'
    )
    
    number_of_questions = forms.IntegerField(
        min_value=1,
        max_value=50,
        initial=10,
        help_text='Number of questions (1-50)',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    difficulty = forms.ChoiceField(
        choices=DIFFICULTY_CHOICES,
        help_text='Select difficulty level',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        required=False,
        help_text='Select a category',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    pdf_file = forms.FileField(
        required=False,
        help_text='Upload a PDF file',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        quiz_type = cleaned_data.get('quiz_type')
        
        if quiz_type == 'pdf':
            if not cleaned_data.get('pdf_file'):
                raise forms.ValidationError('Please upload a PDF file')
        else:  # api
            if not cleaned_data.get('category'):
                raise forms.ValidationError('Please select a category')
        
        return cleaned_data

class ChatMessageForm(forms.ModelForm):
    """Form for sending chat messages"""
    class Meta:
        model = ChatMessage
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ask your AI teacher a question...',
                'style': 'resize: none;'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].label = False

class ChatSessionForm(forms.ModelForm):
    """Form for creating new chat sessions"""
    class Meta:
        model = ChatSession
        fields = ['title', 'quiz']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter session title...'
            }),
            'quiz': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Only show quizzes that have vector stores available
            user_quizzes = Quiz.objects.filter(
                creator=user,
                pdf_file__isnull=False
            ).order_by('-created_at')
            
            # Filter quizzes that have vector stores
            available_quizzes = [quiz for quiz in user_quizzes if quiz.has_vector_store()]
            
            self.fields['quiz'].queryset = Quiz.objects.filter(id__in=[q.id for q in available_quizzes])
            
            # Add help text if no quizzes with vector stores are available
            if not available_quizzes:
                self.fields['quiz'].help_text = "No quizzes with processed vector stores found. Create a quiz with a PDF first to enable context-aware chat."
                self.fields['quiz'].widget.attrs['disabled'] = 'disabled' 