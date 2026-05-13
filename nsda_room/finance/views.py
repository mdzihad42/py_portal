from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils import timezone
from .models import Fine
from accounts.mixins import TeacherOrAdminRequiredMixin

class FineListView(LoginRequiredMixin, ListView):
    model = Fine
    template_name = 'finance/fine_list.html'
    context_object_name = 'fines'

    def get_queryset(self):
        if self.request.user.is_teacher or self.request.user.is_admin_user:
            return Fine.objects.all()
        return Fine.objects.filter(student=self.request.user)

class FineCreateView(TeacherOrAdminRequiredMixin, CreateView):
    model = Fine
    fields = ['student', 'amount', 'reason']
    template_name = 'finance/fine_form.html'
    success_url = reverse_lazy('finance:fine_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, f"Fine added for {form.instance.student.username}")
        return super().form_valid(form)

class MarkPaidView(TeacherOrAdminRequiredMixin, View):
    def post(self, request, pk):
        fine = get_object_or_404(Fine, pk=pk)
        fine.is_paid = True
        fine.paid_at = timezone.now()
        fine.save()
        messages.success(request, f"Fine for {fine.student.username} marked as paid.")
        return redirect('finance:fine_list')
