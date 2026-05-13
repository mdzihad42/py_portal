from django.contrib import admin
from .models import Quiz, Question, Option, QuizSubmission

class OptionInline(admin.TabularInline):
    model = Option
    extra = 4

class QuestionAdmin(admin.ModelAdmin):
    inlines = [OptionInline]
    list_display = ['text', 'quiz', 'marks']
    list_filter = ['quiz']

class QuestionInline(admin.StackedInline):
    model = Question
    extra = 1

class QuizAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by', 'duration_minutes', 'is_active']
    list_filter = ['is_active', 'created_by']
    search_fields = ['title']
    
    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Option)
admin.site.register(QuizSubmission)
