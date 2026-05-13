from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from .models import Quiz, Question, Option, QuizSubmission
from accounts.mixins import TeacherOrAdminRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, CreateView

class QuizListView(ListView):
    model = Quiz
    template_name = 'exams/quiz_list.html'
    context_object_name = 'quizzes'

    def get_queryset(self):
        return Quiz.objects.filter(is_active=True).order_by('-created_at')

class QuizDetailView(DetailView):
    model = Quiz
    template_name = 'exams/quiz_detail.html'
    context_object_name = 'quiz'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['submission'] = QuizSubmission.objects.filter(
                quiz=self.object, student=self.request.user
            ).first()
        return context

class TakeQuizView(LoginRequiredMixin, View):
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
        
        # RESTRICTION: Only students can take exams
        if not request.user.is_student:
            messages.error(request, "Teachers and Admins cannot take exams. Please use the results view.")
            return redirect('exams:quiz_detail', pk=pk)

        # Check if already submitted
        if QuizSubmission.objects.filter(quiz=quiz, student=request.user, is_completed=True).exists():
            messages.warning(request, "You have already completed this quiz.")
            return redirect('exams:quiz_detail', pk=pk)
        
        questions = quiz.questions.all().prefetch_related('options')
        return render(request, 'exams/take_quiz.html', {'quiz': quiz, 'questions': questions})

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, is_active=True)
        
        if not request.user.is_student:
            return redirect('exams:quiz_detail', pk=pk)

        questions = quiz.questions.all()
        score = 0
        
        for q in questions:
            selected_option_id = request.POST.get(f'question_{q.id}')
            if selected_option_id:
                selected_option = Option.objects.filter(id=selected_option_id, question=q).first()
                if selected_option and selected_option.is_correct:
                    score += q.marks
        
        submission, created = QuizSubmission.objects.get_or_create(
            quiz=quiz, student=request.user
        )
        submission.score = score
        submission.is_completed = True
        submission.save()
        
        messages.success(request, f"Quiz submitted! Your score: {score}")
        return redirect('exams:quiz_detail', pk=pk)

class QuizResultsView(TeacherOrAdminRequiredMixin, DetailView):
    """View for teachers to see all submissions for a quiz."""
    model = Quiz
    template_name = 'exams/quiz_results.html'
    context_object_name = 'quiz'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submissions'] = self.object.submissions.select_related('student').order_by('-score')
        return context

class ResetSubmissionView(TeacherOrAdminRequiredMixin, View):
    """View for teachers to delete a student's submission so they can retake it."""
    def post(self, request, pk):
        submission = get_object_or_404(QuizSubmission, pk=pk)
        quiz_id = submission.quiz.id
        student_name = submission.student.username
        submission.delete()
        messages.success(request, f"Submission for {student_name} has been reset. They can now retake the exam.")
        return redirect('exams:quiz_results', pk=quiz_id)

class AddQuestionView(TeacherOrAdminRequiredMixin, View):
    """View to add a question and its options to a quiz."""
    def get(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
        return render(request, 'exams/add_question.html', {'quiz': quiz})

    def post(self, request, pk):
        quiz = get_object_or_404(Quiz, pk=pk, created_by=request.user)
        question_text = request.POST.get('question_text')
        marks = request.POST.get('marks', 1)
        
        # Create Question
        question = Question.objects.create(quiz=quiz, text=question_text, marks=marks)
        
        # Create Options
        options = request.POST.getlist('option_text')
        correct_index = int(request.POST.get('correct_option', 0))
        
        for i, text in enumerate(options):
            if text.strip():
                Option.objects.create(
                    question=question,
                    text=text,
                    is_correct=(i == correct_index)
                )
        
        messages.success(request, "Question added successfully!")
        if 'add_another' in request.POST:
            return redirect('exams:add_question', pk=pk)
        return redirect('exams:teacher_quiz_list')

# Teacher views
class QuizCreateView(TeacherOrAdminRequiredMixin, CreateView):
    model = Quiz
    fields = ['title', 'description', 'duration_minutes', 'total_marks']
    template_name = 'exams/quiz_form.html'
    success_url = '/exams/manage/'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class TeacherQuizListView(TeacherOrAdminRequiredMixin, ListView):
    model = Quiz
    template_name = 'exams/teacher_quiz_list.html'
    context_object_name = 'quizzes'

    def get_queryset(self):
        return Quiz.objects.filter(created_by=self.request.user).order_by('-created_at')
