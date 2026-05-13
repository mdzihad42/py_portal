from django.contrib import admin
from .models import Debate, DebateRegistration, DebateRound, DebateResult


@admin.register(Debate)
class DebateAdmin(admin.ModelAdmin):
    list_display = ('title', 'format', 'date', 'time', 'status', 'created_by', 'registered_count')
    list_filter = ('format', 'status', 'date')
    search_fields = ('title', 'description', 'topic')

    def registered_count(self, obj):
        return obj.registrations.count()
    registered_count.short_description = 'Participants'


@admin.register(DebateRegistration)
class DebateRegistrationAdmin(admin.ModelAdmin):
    list_display = ('student', 'debate', 'team', 'registered_at')
    list_filter = ('team', 'registered_at')


@admin.register(DebateRound)
class DebateRoundAdmin(admin.ModelAdmin):
    list_display = ('debate', 'round_number', 'created_at')


@admin.register(DebateResult)
class DebateResultAdmin(admin.ModelAdmin):
    list_display = ('student', 'debate', 'score', 'rank', 'graded_by', 'created_at')
    list_filter = ('created_at',)
