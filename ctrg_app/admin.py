from django.contrib import admin

from .models import (
    Auditlogs,
    Departments,
    Grantcycles,
    Proposals,
    Proposaldocuments,
    Reviewassignments,
    Reviewers,
    Schools,
    SrcChairs,
    Stage1Reviews,
    Stage2Reviews,
    Users,
)


@admin.register(SrcChairs)
class SrcChairsAdmin(admin.ModelAdmin):
    list_display = ("src_id", "user", "school", "start_date", "end_date", "is_active")
    list_select_related = ("user", "school")
    fields = ("user", "school", "start_date", "end_date", "is_active")


admin.site.register(Users)
admin.site.register(Departments)
admin.site.register(Schools)
admin.site.register(Grantcycles)
admin.site.register(Proposals)
admin.site.register(Proposaldocuments)
admin.site.register(Reviewers)
admin.site.register(Reviewassignments)
admin.site.register(Stage1Reviews)
admin.site.register(Stage2Reviews)
admin.site.register(Auditlogs)
