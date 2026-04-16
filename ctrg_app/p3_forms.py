# # p3_forms.py
# from django import forms
#
# from django import forms
# from .models import Departments
#
# class ProposalSubmitForm(forms.Form):
#     title = forms.CharField(max_length=255, label="Proposal Title")
#
#     # Department shown by name, saves department_id
#     department = forms.ModelChoiceField(
#         queryset=Departments.objects.all().order_by("department_name"),
#         empty_label="Select Department",
#         label="Department"
#     )
#
#     co_investigators = forms.CharField(
#         widget=forms.Textarea(attrs={"rows": 3}),
#         required=False,
#         label="Co-investigators (optional)"
#     )
#     fund_requested = forms.DecimalField(max_digits=12, decimal_places=2, label="Fund Requested")
#
#     proposal_file = forms.FileField(required=True, label="Proposal File")
#     application_template_file = forms.FileField(required=True, label="Application Template File")
#
#
# class RevisionSubmitForm(forms.Form):
#     revised_proposal_file = forms.FileField(required=True)
#     response_to_reviewers_file = forms.FileField(required=False)
#
#
# class Stage1DecisionForm(forms.Form):
#     DECISIONS = [
#         ("STAGE1_REJECTED", "Reject"),
#         ("ACCEPTED_NO_CORRECTIONS", "Accept (No Corrections Required)"),
#         ("REVISION_REQUESTED", "Tentatively Accept (Revision Required)"),
#     ]
#     decision = forms.ChoiceField(choices=DECISIONS)
#     remarks = forms.CharField(widget=forms.Textarea, required=False)
#
#
# class FinalDecisionForm(forms.Form):
#     FINAL = [
#         ("FINAL_ACCEPTED", "Final Accepted"),
#         ("FINAL_REJECTED", "Final Rejected"),
#     ]
#     final_decision = forms.ChoiceField(choices=FINAL)
#     final_grant_amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False)
#     final_remarks = forms.CharField(widget=forms.Textarea, required=False)


# ctrg_app/p3_forms.py
from django import forms
from .models import Departments


class ProposalSubmitForm(forms.Form):
    title = forms.CharField(max_length=255, label="Proposal Title")
    department = forms.ModelChoiceField(
        queryset=Departments.objects.all().order_by("department_name"),
        empty_label="Select Department",
        label="Department"
    )
    co_investigators = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        label="Co-investigators (optional)"
    )
    fund_requested = forms.DecimalField(max_digits=12, decimal_places=2, label="Fund Requested")
    proposal_file = forms.FileField(required=True, label="Proposal File")
    application_template_file = forms.FileField(required=True, label="Application Template File")


class RevisionSubmitForm(forms.Form):
    revised_proposal_file = forms.FileField(required=True)
    response_to_reviewers_file = forms.FileField(required=False)


class Stage1DecisionForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            ("REJECT", "Reject"),
            ("ACCEPT", "Accept (No Corrections Required)"),
            ("TENTATIVE", "Tentatively Accept (Revision Required)"),
        ],
        required=True,
    )
    remarks = forms.CharField(widget=forms.Textarea, required=False)


class FinalDecisionForm(forms.Form):
    final_decision = forms.ChoiceField(
        choices=[
            ("ACCEPTED", "Final Accepted"),
            ("REJECTED", "Final Rejected"),
        ],
        required=True,
    )
    final_grant_amount = forms.DecimalField(max_digits=12, decimal_places=2, required=False)
    final_remarks = forms.CharField(widget=forms.Textarea, required=False)