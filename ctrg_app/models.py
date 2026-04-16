from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class Auditlogs(models.Model):
    audit_id = models.AutoField(primary_key=True)
    actor_user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, blank=True, null=True)
    action_type = models.CharField(max_length=50)
    target_entity = models.CharField(max_length=50)
    target_id = models.IntegerField()
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.action_type} on {self.target_entity} (ID: {self.target_id}) by {self.actor_user}"

    class Meta:
        managed = False
        db_table = 'auditlogs'
        verbose_name_plural = 'Audit Logs'


class Departments(models.Model):
    department_id = models.AutoField(primary_key=True)
    department_name = models.CharField(unique=True, max_length=100)
    school = models.ForeignKey('Schools', null=True, blank=True, on_delete=models.SET_NULL, db_column='school_id')

    def __str__(self):
        return self.department_name

    class Meta:
        managed = False
        db_table = 'departments'
        verbose_name_plural = 'Departments'


class Schools(models.Model):
    school_id = models.AutoField(primary_key=True)
    school_name = models.CharField(max_length=100)

    def __str__(self):
        return self.school_name

    class Meta:
        managed = False
        db_table = 'schools'
        verbose_name_plural = 'Schools'


class Grantcycles(models.Model):
    cycle_id = models.AutoField(primary_key=True)
    school = models.ForeignKey('Schools', null=True, blank=True, on_delete=models.SET_NULL, db_column='school_id')
    created_by_src = models.ForeignKey('SrcChairs', models.DO_NOTHING, blank=True, null=True)
    cycle_name = models.CharField(max_length=100)
    year = models.IntegerField()
    stage1_start_date = models.DateTimeField(blank=True, null=True)
    stage1_end_date = models.DateTimeField(blank=True, null=True)
    revision_duration_days = models.DateTimeField(blank=True, null=True)
    stage2_start_date = models.DateTimeField(blank=True, null=True)
    stage2_end_date = models.DateTimeField(blank=True, null=True)
    acceptance_threshold = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    max_reviewers_per_proposal = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.cycle_name} ({self.year}) - {self.school}"

    class Meta:
        managed = False
        db_table = 'grantcycles'
        verbose_name_plural = 'Grant Cycles'


class Proposaldocuments(models.Model):
    document_id = models.AutoField(primary_key=True)
    proposal = models.ForeignKey('Proposals', models.DO_NOTHING)
    document_type = models.CharField(max_length=8)
    file_path = models.CharField(max_length=255)
    version = models.IntegerField(blank=True, null=True)
    uploaded_at = models.DateTimeField()

    def __str__(self):
        return f"{self.document_type} - Proposal #{self.proposal_id} (v{self.version})"

    class Meta:
        managed = False
        db_table = 'proposaldocuments'
        verbose_name_plural = 'Proposal Documents'


class Proposals(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('UNDER_STAGE_1_REVIEW', 'Under Stage 1 Review'),
        ('STAGE_1_REJECTED', 'Stage 1 Rejected'),
        ('ACCEPTED_NO_CORRECTIONS', 'Accepted No Corrections'),
        ('TENTATIVELY_ACCEPTED', 'Tentatively Accepted'),
        ('REVISION_REQUESTED', 'Revision Requested'),
        ('REVISED_PROPOSAL_SUBMITTED', 'Revised Proposal Submitted'),
        ('UNDER_STAGE_2_REVIEW', 'Under Stage 2 Review'),
        ('FINAL_ACCEPTED', 'Final Accepted'),
        ('FINAL_REJECTED', 'Final Rejected'),
    ]

    STAGE1_DECISION_CHOICES = [
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('TENTATIVE', 'Tentative'),
    ]

    FINAL_DECISION_CHOICES = [
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    proposal_id = models.AutoField(primary_key=True)
    cycle = models.ForeignKey(Grantcycles, models.DO_NOTHING)
    pi_user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)
    department = models.ForeignKey(Departments, models.DO_NOTHING)
    unique_code = models.CharField(unique=True, max_length=50)
    title = models.CharField(max_length=255)
    co_investigators = models.TextField(blank=True, null=True)
    fund_requested = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=26, choices=STATUS_CHOICES)
    stage1_decision = models.CharField(max_length=9, blank=True, null=True, choices=STAGE1_DECISION_CHOICES)
    stage1_decision_date = models.DateTimeField(blank=True, null=True)
    stage1_remarks = models.TextField(blank=True, null=True)
    revision_deadline = models.DateTimeField(blank=True, null=True)
    final_decision = models.CharField(max_length=8, blank=True, null=True, choices=FINAL_DECISION_CHOICES)
    final_grant_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    final_remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.title} [{self.unique_code}] - {self.status}"

    class Meta:
        managed = False
        db_table = 'proposals'
        verbose_name_plural = 'Proposals'


class Reviewassignments(models.Model):
    assignment_id = models.AutoField(primary_key=True)
    proposal = models.ForeignKey(Proposals, models.DO_NOTHING)
    reviewer = models.ForeignKey('Reviewers', models.DO_NOTHING)
    assigned_at = models.DateTimeField()
    is_active = models.BooleanField(blank=True, null=True)

    acceptance_status = models.CharField(
        max_length=10,
        choices=[
            ('PENDING', 'Pending'),
            ('ACCEPTED', 'Accepted'),
            ('REJECTED', 'Rejected'),
        ],
        default='PENDING'
    )
    def __str__(self):
        return f"Reviewer: {self.reviewer} → Proposal: {self.proposal}"

    class Meta:
        managed = False
        db_table = 'reviewassignments'
        verbose_name_plural = 'Review Assignments'
        unique_together = (('proposal', 'reviewer'),)


class Reviewers(models.Model):
    reviewer_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)
    department = models.ForeignKey(Departments, models.DO_NOTHING)
    max_review_load = models.IntegerField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} ({self.department})"

    class Meta:
        managed = False
        db_table = 'reviewers'
        verbose_name_plural = 'Reviewers'


class SrcChairs(models.Model):
    src_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING)
    school = models.ForeignKey('Schools', null=True, blank=True, on_delete=models.SET_NULL, db_column='school_id')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)

    def __str__(self):
        return f"SRC Chair: {self.user} ({self.school})"

    class Meta:
        managed = False
        db_table = 'src_chairs'
        verbose_name_plural = 'SRC Chairs'


class Stage1Reviews(models.Model):
    stage1_review_id = models.AutoField(primary_key=True)
    assignment = models.OneToOneField(Reviewassignments, models.DO_NOTHING)
    score_originality = models.IntegerField(blank=True, null=True)
    score_clarity = models.IntegerField(blank=True, null=True)
    score_lit_review = models.IntegerField(blank=True, null=True)
    score_methodology = models.IntegerField(blank=True, null=True)
    score_impact = models.IntegerField(blank=True, null=True)
    score_publication = models.IntegerField(blank=True, null=True)
    score_budget = models.IntegerField(blank=True, null=True)
    score_timeframe = models.IntegerField(blank=True, null=True)
    total_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    narrative_comments = models.TextField(blank=True, null=True)
    is_submitted = models.BooleanField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        status = "Submitted" if self.is_submitted else "Draft"
        return f"Stage 1 Review - {self.assignment} [{status}] - {self.total_percentage}%"

    class Meta:
        managed = False
        db_table = 'stage1reviews'
        verbose_name_plural = 'Stage 1 Reviews'


class Stage2Reviews(models.Model):
    CONCERNS_CHOICES = [
        ('YES', 'Yes'),
        ('PARTIALLY', 'Partially'),
        ('NO', 'No'),
    ]

    RECOMMENDATION_CHOICES = [
        ('ACCEPT', 'Accept'),
        ('REJECT', 'Reject'),
    ]

    stage2_review_id = models.AutoField(primary_key=True)
    assignment = models.OneToOneField(Reviewassignments, models.DO_NOTHING)
    concerns_addressed = models.CharField(max_length=9, choices=CONCERNS_CHOICES)
    recommendation = models.CharField(max_length=6, choices=RECOMMENDATION_CHOICES)
    revised_score = models.IntegerField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField()

    def __str__(self):
        return f"Stage 2 Review - {self.assignment} - {self.recommendation}"

    class Meta:
        managed = False
        db_table = 'stage2reviews'
        verbose_name_plural = 'Stage 2 Reviews'


class Users(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    department = models.ForeignKey('Departments', null=True, blank=True, on_delete=models.SET_NULL, db_column='department_id')
    area_of_expertise = models.TextField(null=True, blank=True)
    profile_picture = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.email})"

    class Meta:
        db_table = 'users'
        verbose_name_plural = 'Users'
