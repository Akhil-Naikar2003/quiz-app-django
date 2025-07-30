from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.conf import settings
import os
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
import json
import re
from .models import Quiz, Question, Choice, UserAnswer, QuizAttempt, ChatSession, ChatMessage, UserProfile
from .forms import (
    UserRegistrationForm, QuizForm, QuestionForm, 
    ChoiceForm, QuizQuestionForm, OpenTDBQuizForm,
    ChatMessageForm, ChatSessionForm
)
from .vector_store import PDFProcessor
import requests
from django.views.generic import FormView
import random
from langchain.chains import RetrievalQA

# Load environment variables
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
#done
def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'quiz_app/home.html', {'quizzes': []})
#done
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    return render(request, 'quiz_app/register.html', {'form': form})
#done
def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'quiz_app/login.html')


#done
@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

# def fetch_questions(text_content, difficulty, number):
#     RESPONSE_JSON = {
#         "mcqs": [
#             {
#                 "mcq": "Example question",
#                 "options": {"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
#                 "correct": "A"
#             }
#         ]
#     }

#     # Different prompt templates for variety
#     prompt_templates = [
#         (
#             "Text: {text_content}\n"
#             "You are an expert quiz generator. Create {number} diverse {difficulty} difficulty questions based on the provided text.\n"
#             "Each question should test different aspects: comprehension, application, analysis, and evaluation.\n"
#             "Ensure questions are unique and cover various topics from the text.\n"
#             "Format: {RESPONSE_JSON}"
#         ),
#         (
#             "Content: {text_content}\n"
#             "Generate {number} {difficulty} level multiple choice questions.\n"
#             "Focus on: definitions, processes, relationships, and practical applications.\n"
#             "Make each question distinct and challenging.\n"
#             "Output format: {RESPONSE_JSON}"
#         ),
#         (
#             "Based on this material: {text_content}\n"
#             "Create {number} {difficulty} questions covering different concepts.\n"
#             "Question types: factual recall, conceptual understanding, problem-solving.\n"
#             "Ensure variety in question structure and content.\n"
#             "JSON format: {RESPONSE_JSON}"
#         )
#     ]

#     # Use different prompts for variety
#     selected_template = random.choice(prompt_templates)

#     quiz_prompt_template = PromptTemplate(
#         input_variables=["difficulty", "text_content", "RESPONSE_JSON"],
#         template=selected_template,
#     )

#     llm = ChatGroq(
#         model="gemma2-9b-it",
#         api_key=groq_api_key,
#         temperature=0.8  # Increased temperature for more diversity
#     )
#     chain = LLMChain(llm=llm, prompt=quiz_prompt_template)

#     try:
#         response = chain.run(
#             difficulty=difficulty,
#             text_content=text_content,
#             number=number,
#             RESPONSE_JSON=json.dumps(RESPONSE_JSON),
#         )

#         # Try to find valid JSON in the response
#         try:
#             # First try to parse the entire response as JSON
#             result = json.loads(response)
            
#             # Validate and deduplicate questions
#             if 'mcqs' in result:
#                 questions = result['mcqs']
#                 unique_questions = []
#                 seen_questions = set()
                
#                 for question in questions:
#                     # Create a simple hash for deduplication
#                     question_hash = question.get('mcq', '').lower().strip()
#                     if question_hash and question_hash not in seen_questions:
#                         seen_questions.add(question_hash)
#                         unique_questions.append(question)
                
#                 result['mcqs'] = unique_questions
#                 print(f"Generated {len(unique_questions)} unique questions from {len(questions)} total")
            
#             return result
#         except json.JSONDecodeError:
#             # If that fails, try to find JSON array in the response
#             json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
#             if json_match:
#                 try:
#                     return json.loads(json_match.group(0))
#                 except json.JSONDecodeError:
#                     print(f"Error parsing JSON from response: {response}")
#                     return []
#             else:
#                 print(f"No valid JSON found in response: {response}")
#                 return []
#     except Exception as e:
#         print(f"Error generating questions: {e}")
#         return []


#done(without questin generation)
class CreateQuizView(FormView):
    template_name = 'quiz_app/create_quiz_new.html'
    form_class = OpenTDBQuizForm
    success_url = '/dashboard/'

    def form_valid(self, form):
        quiz_type = form.cleaned_data['quiz_type']
        
        if quiz_type == 'pdf':
            # Use existing PDF quiz creation logic
            return self.handle_pdf_quiz(form)
        else:
            # Handle API  vquiz creation
            return self.handle_api_quiz(form)

    def handle_pdf_quiz(self, form):
        # Reuse existing PDF quiz creation logic
        number_of_questions = form.cleaned_data['number_of_questions']
        print("[DEBUG] Number of questions from form (PDF):", number_of_questions)
        quiz = Quiz.objects.create(
            creator=self.request.user,
            title=f"PDF Quiz {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            difficulty=form.cleaned_data['difficulty'],
        )
        
        try:
            # Ensure media directories exist
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'vector_stores'), exist_ok=True)
            
            # Process the PDF file
            pdf_file = form.cleaned_data['pdf_file']
            quiz.pdf_file = pdf_file
            quiz.save()
            
            pdf_path = os.path.join(settings.MEDIA_ROOT, str(quiz.pdf_file))
            

            # Initialize PDF processor
            
            processor = PDFProcessor()
            
            # Process PDF and create vector store
            vector_store = processor.process_pdf(pdf_path)
            
            # Save vector store for future use
            store_path = os.path.join(settings.MEDIA_ROOT, 'vector_stores', f'quiz_{quiz.id}')
            os.makedirs(store_path, exist_ok=True)
            processor.save_vector_store(vector_store, store_path)
            
            # Generate questions using vector store
            print(f"Requesting {number_of_questions} questions...")
            questions = processor.generate_questions(
                vector_store,
                quiz.difficulty,
                number_of_questions,
                quiz_id=quiz.id
            )

            if not questions:
                raise Exception("Failed to generate questions")

            print(f"Successfully generated {len(questions)} questions out of {number_of_questions} requested")

            # Create questions and choices
            question_order = 0
            for q_data in questions:
                question = Question.objects.create(
                    quiz=quiz,
                    text=q_data['mcq'],
                    order=question_order
                )
                
                choice_order = 0
                for option_letter, option_text in q_data['options'].items():
                    Choice.objects.create(
                        question=question,
                        text=option_text,
                        is_correct=(option_letter == q_data['correct']),
                        order=choice_order
                    )
                    choice_order += 1
                question_order += 1

            # Show success message with actual vs requested questions
            if len(questions) == number_of_questions:
                messages.success(self.request, f'Quiz created successfully with {len(questions)} questions!')
            else:
                messages.success(self.request, f'Quiz created with {len(questions)} questions (requested {number_of_questions}). Some questions may have been filtered due to duplicates or content limitations.')
            return redirect('dashboard')

        except Exception as e:
            messages.error(self.request, f'Error creating quiz: {str(e)}')
            quiz.delete()
            return self.form_invalid(form)

    def handle_api_quiz(self, form):
        try:
            number_of_questions = form.cleaned_data['number_of_questions']
            print("[DEBUG] Number of questions from form (API):", number_of_questions)
            # Build API URL
            api_url = "https://opentdb.com/api.php"
            params = {
                'amount': number_of_questions,
                'category': form.cleaned_data['category'],
                'difficulty': form.cleaned_data['difficulty'],
                'type': 'multiple'
            }
            
            # Make API request
            response = requests.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['response_code'] != 0:
                raise Exception("API returned an error")
            
            # Create quiz
            quiz = Quiz.objects.create(
                creator=self.request.user,
                title=f"API Quiz - {dict(form.CATEGORY_CHOICES)[int(form.cleaned_data['category'])]}",
                difficulty=form.cleaned_data['difficulty'],
            )
            
            # Create questions and choices
            question_order = 0
            for q_data in data['results']:
                question = Question.objects.create(
                    quiz=quiz,
                    text=q_data['question'],
                    order=question_order
                )
                
                # Combine correct and incorrect answers
                all_answers = [q_data['correct_answer']] + q_data['incorrect_answers']
                # Shuffle answers
                random.shuffle(all_answers)
                
                # Create choices
                choice_order = 0
                for i, answer in enumerate(all_answers):
                    Choice.objects.create(
                        question=question,
                        text=answer,
                        is_correct=(answer == q_data['correct_answer']),
                        order=choice_order
                    )
                    choice_order += 1
                question_order += 1
            
            messages.success(self.request, 'Quiz created successfully!')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(self.request, f'Error creating quiz: {str(e)}')
            return self.form_invalid(form)


#should be delated
@login_required
def add_questions(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.quiz = quiz
            question.save()
            return redirect('add_choices', question_id=question.id)
    else:
        question_form = QuestionForm()
    return render(request, 'quiz_app/add_questions.html', {
        'quiz': quiz,
        'form': question_form
    })

#should be delated
@login_required
def add_choices(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        form = ChoiceForm(request.POST)
        if form.is_valid():
            choice = form.save(commit=False)
            choice.question = question
            choice.save()
            return redirect('add_choices', question_id=question.id)
    else:
        form = ChoiceForm()
    return render(request, 'quiz_app/add_choices.html', {
        'question': question,
        'form': form
    })

#done
@login_required
def take_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Check if user can take another attempt
    if not quiz.can_user_attempt(request.user):
        messages.warning(request, f'You have reached the maximum number of attempts ({quiz.max_attempts}) for this quiz.')
        return redirect('dashboard')
    
    questions = list(quiz.questions.all())
    # print(questions)
    
    # Shuffle questions for variety
    random.shuffle(questions)
    
    # Shuffle choices for each question
    for question in questions:
        choices = list(question.choices.all())
        # print(choices)
        random.shuffle(choices)
        question.shuffled_choices = choices
        # print(question.shuffled_choices)
    
    # Get user's attempt count for display
    attempt_count = quiz.get_user_attempt_count(request.user)
    next_attempt_number = attempt_count + 1
    
    if request.method == 'POST':
        return redirect('submit_quiz', quiz_id=quiz.id)
    
    return render(request, 'quiz_app/take_quiz.html', {
        'quiz': quiz,
        'questions': questions,
        'attempt_count': attempt_count,
        'next_attempt_number': next_attempt_number,
        'max_attempts': quiz.max_attempts
    })
#done
@login_required
def submit_quiz(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    questions = quiz.questions.all()
    
    if request.method == 'POST':
        score = 0
        total_questions = questions.count()
        
        # Calculate the next attempt number for this user and quiz
        previous_attempts = QuizAttempt.objects.filter(
            user=request.user, 
            quiz=quiz
        ).order_by('-attempt_number')
        
        if previous_attempts.exists():
            next_attempt_number = previous_attempts.first().attempt_number + 1
        else:
            next_attempt_number = 1
        
        # Create a new QuizAttempt
        attempt = QuizAttempt.objects.create(
            user=request.user,
            quiz=quiz,
            attempt_number=next_attempt_number,
            score=0,  # Will update after answers are processed
            total_questions=total_questions
        )
        
        user_answers = []
        for question in questions:
            selected_choice_id = request.POST.get(f'question_{question.id}')
            if selected_choice_id:
                selected_choice = Choice.objects.get(id=selected_choice_id)
                ua = UserAnswer.objects.create(
                    attempt=attempt,
                    question=question,
                    selected_choice=selected_choice,
                )
                user_answers.append(ua)
                if selected_choice.is_correct:
                    score += 1
        
        # Update the score in the attempt
        attempt.score = score
        attempt.correct_answers = score
        attempt.completed_at = timezone.now()
        attempt.status = 'completed'
        attempt.save()

        # --- GAMIFICATION ---
        # Ensure user profile exists
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Calculate points (10 per correct answer, 5 for completion, bonus for perfect score)
        points_earned = score * 10 + 5
        if score == total_questions:  # Perfect score bonus
            points_earned += 25
        
        profile.points += points_earned
        
        # Award badges
        badges = profile.badges or []
        new_badges = []
        
        # First win badge
        if len(badges) == 0 and score > 0 and 'First Win' not in badges:
            new_badges.append('First Win')
        
        # Perfect score badge
        if score == total_questions and 'Perfect Score' not in badges:
            new_badges.append('Perfect Score')
        
        # Streak badges (check recent attempts)
        recent_attempts = QuizAttempt.objects.filter(
            user=request.user, 
            status='completed'
        ).order_by('-completed_at')[:5]
        
        if len(recent_attempts) >= 3:
            # Check for 3+ correct answers in a row
            correct_streak = 0
            for attempt in recent_attempts:
                if attempt.correct_answers == attempt.total_questions:
                    correct_streak += 1
                else:
                    break
            
            if correct_streak >= 3 and 'Streak Master' not in badges:
                new_badges.append('Streak Master')
            elif correct_streak >= 2 and 'On Fire' not in badges:
                new_badges.append('On Fire')
        
        # Quiz completion badges
        total_quizzes_taken = QuizAttempt.objects.filter(
            user=request.user, 
            status='completed'
        ).count()
        
        if total_quizzes_taken >= 10 and 'Quiz Veteran' not in badges:
            new_badges.append('Quiz Veteran')
        elif total_quizzes_taken >= 5 and 'Quiz Enthusiast' not in badges:
            new_badges.append('Quiz Enthusiast')
        
        # Add new badges
        badges.extend(new_badges)
        profile.badges = badges
        profile.save()
        
        # Show success message with points and badges
        if new_badges:
            messages.success(request, f'Quiz completed! You earned {points_earned} points and unlocked: {", ".join(new_badges)}')
        else:
            messages.success(request, f'Quiz completed! You earned {points_earned} points.')

        return redirect('quiz_results_detail', quiz_id=quiz.id)
    
    return redirect('take_quiz', quiz_id=quiz.id)

#not use
@login_required
def quiz_results(request):
    # Get all quizzes attempted by the user
    attempted_quizzes = Quiz.objects.filter(
        attempts__user=request.user
    ).distinct().order_by('-created_at')
    
    return render(request, 'quiz_app/quiz_results_1.html', {
        'attempted_quizzes': attempted_quizzes,
        'show_quiz_selection': True,
    })


#done
@login_required
def quiz_results_detail(request, quiz_id):
    quiz = get_object_or_404(Quiz, id=quiz_id)
    attempts = QuizAttempt.objects.filter(user=request.user, quiz=quiz).order_by('-completed_at')
    
    if attempts.count() == 0:
        return redirect('quiz_results')
    
    selected_attempt_id = request.GET.get('attempt')
    if selected_attempt_id:
        selected_attempt = get_object_or_404(QuizAttempt, id=selected_attempt_id, user=request.user, quiz=quiz)
    else:
        selected_attempt = attempts.first()  # Most recent by default
    
    user_answers = UserAnswer.objects.filter(attempt=selected_attempt).select_related('question', 'selected_choice')
    
    # Calculate score and total questions
    score = selected_attempt.score
    total_questions = selected_attempt.total_questions
    percentage = (score / total_questions * 100) if total_questions > 0 else 0
    
    return render(request, 'quiz_app/quiz_results.html', {
        'quiz': quiz,
        'attempts': attempts,
        'selected_attempt': selected_attempt,
        'user_answers': user_answers,
        'score': score,
        'total_questions': total_questions,
        'percentage': percentage,
        'show_quiz_selection': False,
    })


#done
@login_required
def dashboard(request):
    # Get quizzes created by the user
    created_quizzes = Quiz.objects.filter(creator=request.user).order_by('-created_at')
    # print(created_quizzes)
    
    # Get quizzes attempted by the user
    attempted_quizzes = Quiz.objects.filter(
        attempts__user=request.user
    ).distinct().order_by('-created_at')
    # print(attempted_quizzes)

    
    # Combine both sets and remove duplicates
    all_quizzes = list(created_quizzes) + [quiz for quiz in attempted_quizzes if quiz not in created_quizzes]
    
    total_attempts = QuizAttempt.objects.filter(user=request.user).count()
    user_attempts = QuizAttempt.objects.filter(user=request.user)
    total_score = sum(a.score for a in user_attempts)
    total_questions = sum(a.total_questions for a in user_attempts)
    average_score = (total_score / total_questions * 100) if total_questions > 0 else 0

    # Calculate statistics for each quiz
    for quiz in all_quizzes:
        attempts = QuizAttempt.objects.filter(user=request.user, quiz=quiz)
        quiz.attempt_count = attempts.count()
        quiz.can_attempt = quiz.can_user_attempt(request.user)
        quiz.attempts_remaining = quiz.max_attempts - quiz.attempt_count if quiz.max_attempts > 0 else -1  # -1 means unlimited
        
        if attempts.exists():
            quiz.average_score = sum(a.score for a in attempts) / attempts.count()
            # Calculate average percentage safely
            total_questions_sum = sum(a.total_questions for a in attempts)
            if total_questions_sum > 0:
                quiz.average_percentage = (sum((a.score / a.total_questions) for a in attempts) / attempts.count()) * 100
            else:
                quiz.average_percentage = 0
            latest_attempt = attempts.latest('completed_at')
            quiz.user_score = latest_attempt.score
            quiz.total_questions = latest_attempt.total_questions
            quiz.score_percentage = (latest_attempt.score / latest_attempt.total_questions * 100) if latest_attempt.total_questions > 0 else 0
        else:
            quiz.average_score = None
            quiz.average_percentage = None
            quiz.user_score = None
            quiz.total_questions = quiz.questions.count()
            quiz.score_percentage = None

    return render(request, 'quiz_app/dashboard.html', {
        'quizzes': all_quizzes,
        'total_attempts': total_attempts,
        'average_score': average_score,
        'user_profile': getattr(request.user, 'profile', None),
    })
#done
@login_required
def analysis(request):
    # Get all quiz attempts
    quiz_attempts = QuizAttempt.objects.filter(user=request.user).select_related('quiz').order_by('-started_at') #inner join
    
    # Calculate overall statistics
    total_attempts = quiz_attempts.count()
    if total_attempts > 0:
        average_score = sum(attempt.percentage for attempt in quiz_attempts) / total_attempts
    else:
        average_score = 0
    
    return render(request, 'quiz_app/analysis.html', {
        'quiz_attempts': quiz_attempts,
        'total_attempts': total_attempts,
        'average_score': average_score,
    })


#done 
@login_required
def delete_quiz(request, quiz_id):
    """
    Delete a quiz - only the creator can delete their own quiz
    """
    quiz = get_object_or_404(Quiz, id=quiz_id)
    
    # Security check: only the creator can delete the quiz
    if quiz.creator != request.user:
        messages.error(request, 'You do not have permission to delete this quiz.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Store quiz title for success message
        quiz_title = quiz.title
        
        # Clean up associated files
        try:
            # Delete PDF file if it exists
            if quiz.pdf_file:
                pdf_path = os.path.join(settings.MEDIA_ROOT, str(quiz.pdf_file))
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)
            
            # Delete vector store files if they exist
            vector_store_path = os.path.join(settings.MEDIA_ROOT, 'vector_stores', f'quiz_{quiz.id}')
            if os.path.exists(vector_store_path):
                import shutil
                shutil.rmtree(vector_store_path)
        except Exception as e:
            # Log the error but don't stop the deletion
            print(f"Error cleaning up files for quiz {quiz.id}: {e}")
        
        # Delete the quiz (this will cascade delete all related data)
        quiz.delete()
        
        messages.success(request, f'Quiz "{quiz_title}" has been deleted successfully.')
        return redirect('dashboard')
    
    # Show confirmation page
    return render(request, 'quiz_app/delete_quiz_confirm.html', {
        'quiz': quiz
    })

# Chat Views
@login_required
def chat_sessions(request):
    """List all chat sessions for the user"""
    sessions = ChatSession.objects.filter(user=request.user).order_by('-last_message_at', '-created_at')
    
    if request.method == 'POST':
        form = ChatSessionForm(request.POST, user=request.user)
        if form.is_valid():
            session = form.save(commit=False)
            session.user = request.user
            session.save() 
            messages.success(request, 'New chat session created!')
            return redirect('chat_session', session_id=session.id)
    else:
        form = ChatSessionForm(user=request.user)
    
    return render(request, 'quiz_app/chat_sessions.html', {
        'sessions': sessions,
        'form': form
    })

def strip_unsupported_chars(text):
    """Removes 4-byte Unicode characters not supported by standard utf8."""
    return re.sub(r'[\U00010000-\U0010FFFF]', '', text)

@login_required
def chat_session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    messages_list = []  # Start with an empty list

    if request.method == 'POST':
        form = ChatMessageForm(request.POST)
        if form.is_valid():
            user_message = form.save(commit=False)
            user_message.session = session
            user_message.message_type = 'user'
            # Clean the user's message before saving
            user_message.content = strip_unsupported_chars(user_message.content)
            user_message.save()

            # Generate AI response
            ai_response_content = generate_ai_response(session, user_message.content)
            
            # Clean the AI's response before saving
            cleaned_ai_content = strip_unsupported_chars(ai_response_content)

            # Save AI response
            ChatMessage.objects.create(
                session=session,
                content=cleaned_ai_content,
                message_type='assistant'
            )
            
            # After posting, load all messages for display
            messages_list = session.messages.all().order_by('timestamp')
            
            # Update last activity timestamp
            session.last_message_at = timezone.now()
            session.save()
            
            # We display the messages, so we can clear the form
            form = ChatMessageForm()
    else:
        form = ChatMessageForm()
        # On GET request, messages_list remains empty, so history isn't shown

    return render(request, 'quiz_app/chat_session.html', {
        'session': session,
        'messages': messages_list,
        'form': form
    })

@login_required
def delete_chat_session(request, session_id):
    """Delete a chat session"""
    session = get_object_or_404(ChatSession, id=session_id, user=request.user)
    
    if request.method == 'POST':
        session_title = session.title
        session.delete()
        messages.success(request, f'Chat session "{session_title}" deleted successfully.')
        return redirect('chat_sessions')
    
    return render(request, 'quiz_app/delete_chat_session_confirm.html', {
        'session': session
    })

def generate_ai_response(session, user_message):
    """Generate AI response using RAG with existing vector store"""
    try:
        # Initialize PDF processor
        processor = PDFProcessor()
        
        # Load existing vector store for the quiz if available
        vector_store = None
        if session.quiz and session.quiz.pdf_file:
            # Check if vector store exists for this quiz
            vector_store_path = os.path.join(settings.MEDIA_ROOT, 'vector_stores', f'quiz_{session.quiz.id}')
            if os.path.exists(vector_store_path):
                try:
                    vector_store = processor.load_vector_store(vector_store_path)
                    print(f"Loaded existing vector store for quiz {session.quiz.id}")
                except Exception as e:
                    print(f"Error loading vector store: {e}")
                    # Fallback: recreate vector store from PDF
                    pdf_path = os.path.join(settings.MEDIA_ROOT, str(session.quiz.pdf_file))
                    if os.path.exists(pdf_path):
                        vector_store = processor.process_pdf(pdf_path)
                        # Save the recreated vector store
                        processor.save_vector_store(vector_store, vector_store_path)
                        print(f"Recreated and saved vector store for quiz {session.quiz.id}")
            else:
                # Vector store doesn't exist, create it from PDF
                pdf_path = os.path.join(settings.MEDIA_ROOT, str(session.quiz.pdf_file))
                if os.path.exists(pdf_path):
                    vector_store = processor.process_pdf(pdf_path)
                    # Save the new vector store
                    os.makedirs(vector_store_path, exist_ok=True)
                    processor.save_vector_store(vector_store, vector_store_path)
                    print(f"Created and saved new vector store for quiz {session.quiz.id}")
        
        # Create chat history context
        chat_history = []
        #similar(same) to ChatMessage.objects.filter(session_id=1).order_by('-timestamp')[:10]
        recent_messages = session.messages.order_by('-timestamp')[:10]  # Last 10 messages
        for msg in reversed(recent_messages):  # Reverse to get chronological order
            role = "user" if msg.message_type == "user" else "assistant"
            chat_history.append({"role": role, "content": msg.content})
        
        # Create system prompt for teacher role
        system_prompt = """You are an AI teacher assistant helping students understand the course material. 
        You should:
        1. Answer questions based on the provided context
        2. Explain concepts clearly and in simple terms
        3. Provide examples when helpful
        4. Ask follow-up questions to encourage deeper understanding
        5. Be encouraging and supportive
        6. If you don't know something, say so rather than guessing
        
        Use the context from the uploaded PDF to provide accurate answers."""
        
        if vector_store:
            # Use RAG with vector store
            qa_chain = RetrievalQA.from_chain_type(
                llm=processor.llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(search_kwargs={"k": 3})
            )
            
            # Create context-aware prompt
            context_prompt = f"""
            {system_prompt}
            
            Chat History:
            {chat_history}
            
            Current Question: {user_message}
            
            Please provide a helpful and educational response based on the context.
            """
            
            response = qa_chain.invoke(context_prompt)
            return response['result']
        else:
            # Fallback to general response without PDF context
            general_prompt = f"""
            {system_prompt}
            
            Chat History:
            {chat_history}
            
            Current Question: {user_message}
            
            Please provide a helpful response. Note: I don't have access to specific course materials for this session.
            """
            
            response = processor.llm.invoke(general_prompt)
            return response.content
            
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return "I apologize, but I'm having trouble processing your question right now. Please try again or contact support if the issue persists."
