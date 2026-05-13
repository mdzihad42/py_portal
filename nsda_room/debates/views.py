from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q

from accounts.mixins import (
    StudentRequiredMixin, TeacherOrAdminRequiredMixin,
)
from .models import Debate, DebateRegistration, DebateResult
from .forms import DebateForm, DebateRegistrationForm, ResultForm


class DebateListView(LoginRequiredMixin, ListView):
    model = Debate
    template_name = 'debates/debate_list.html'
    context_object_name = 'debates'
    paginate_by = 10

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.request.user.is_student:
            registered_ids = DebateRegistration.objects.filter(
                student=self.request.user
            ).values_list('debate_id', flat=True)
            ctx['registered_ids'] = set(registered_ids)
        ctx['status_filter'] = self.request.GET.get('status', '')
        return ctx


class DebateDetailView(LoginRequiredMixin, DetailView):
    model = Debate
    template_name = 'debates/debate_detail.html'
    context_object_name = 'debate'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['participants'] = self.object.registrations.select_related('student').all()
        ctx['results'] = self.object.results.select_related('student').all()

        if self.request.user.is_student:
            ctx['is_registered'] = DebateRegistration.objects.filter(
                debate=self.object, student=self.request.user
            ).exists()
            ctx['my_result'] = DebateResult.objects.filter(
                debate=self.object, student=self.request.user
            ).first()
            ctx['register_form'] = DebateRegistrationForm()

        if self.request.user.is_teacher or self.request.user.is_admin_user:
            ctx['result_form'] = ResultForm()
        return ctx


class DebateCreateView(TeacherOrAdminRequiredMixin, CreateView):
    model = Debate
    form_class = DebateForm
    template_name = 'debates/debate_form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Debate created successfully!')
        return super().form_valid(form)


class DebateUpdateView(TeacherOrAdminRequiredMixin, UpdateView):
    model = Debate
    form_class = DebateForm
    template_name = 'debates/debate_form.html'

    def form_valid(self, form):
        messages.success(self.request, 'Debate updated successfully!')
        return super().form_valid(form)


class DebateDeleteView(TeacherOrAdminRequiredMixin, DeleteView):
    model = Debate
    template_name = 'debates/debate_confirm_delete.html'
    success_url = reverse_lazy('debates:list')

    def form_valid(self, form):
        messages.success(self.request, 'Debate deleted.')
        return super().form_valid(form)


class DebateRegisterView(StudentRequiredMixin, View):
    """Student registers for a debate."""

    def post(self, request, pk):
        debate = get_object_or_404(Debate, pk=pk)

        if debate.is_full:
            messages.error(request, 'This debate is full.')
            return redirect('debates:detail', pk=pk)

        if DebateRegistration.objects.filter(debate=debate, student=request.user).exists():
            messages.warning(request, 'You are already registered.')
            return redirect('debates:detail', pk=pk)

        form = DebateRegistrationForm(request.POST)
        if form.is_valid():
            reg = form.save(commit=False)
            reg.debate = debate
            reg.student = request.user
            reg.save()
            messages.success(request, f'Registered for "{debate.title}" successfully!')
        return redirect('debates:detail', pk=pk)


class DebateUnregisterView(StudentRequiredMixin, View):
    """Student cancels registration."""

    def post(self, request, pk):
        debate = get_object_or_404(Debate, pk=pk)
        reg = DebateRegistration.objects.filter(
            debate=debate, student=request.user
        ).first()
        if reg:
            reg.delete()
            messages.info(request, 'Registration cancelled.')
        return redirect('debates:detail', pk=pk)


class ResultInputView(TeacherOrAdminRequiredMixin, View):
    """Teacher inputs results for a student."""

    def post(self, request, pk):
        debate = get_object_or_404(Debate, pk=pk)
        student_id = request.POST.get('student_id')

        form = ResultForm(request.POST)
        if form.is_valid():
            result, created = DebateResult.objects.update_or_create(
                debate=debate,
                student_id=student_id,
                defaults={
                    'score': form.cleaned_data['score'],
                    'rank': form.cleaned_data['rank'],
                    'feedback': form.cleaned_data['feedback'],
                    'graded_by': request.user,
                }
            )
            action = 'added' if created else 'updated'
            messages.success(request, f'Result {action} successfully!')
        else:
            messages.error(request, 'Invalid result data.')
        return redirect('debates:detail', pk=pk)


class MyDebatesView(StudentRequiredMixin, ListView):
    """Student view: my registered debates."""
    template_name = 'debates/my_debates.html'
    context_object_name = 'registrations'
    paginate_by = 10

    def get_queryset(self):
        return DebateRegistration.objects.filter(
            student=self.request.user
        ).select_related('debate').order_by('-debate__date')


class MyResultsView(StudentRequiredMixin, ListView):
    """Student view: my results across all debates."""
    template_name = 'debates/my_results.html'
    context_object_name = 'results'
    paginate_by = 10

    def get_queryset(self):
        return DebateResult.objects.filter(
            student=self.request.user
        ).select_related('debate').order_by('-created_at')
