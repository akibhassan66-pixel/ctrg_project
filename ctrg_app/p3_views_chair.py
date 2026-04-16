# ctrg_app/p3_views_chair.py

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Avg
from django.contrib import messages
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from .models import (
    Proposals,
    Stage1Reviews,
    Stage2Reviews,
    Proposaldocuments,
    Auditlogs,
    Reviewassignments,
    SrcChairs,
)

from .p3_forms import Stage1DecisionForm, FinalDecisionForm


def is_chair(user):
    return SrcChairs.objects.filter(user=user, is_active=True).exists()


# ----------------------------------------
# STAGE 1 DECISION PAGE
# ----------------------------------------
@login_required
def chair_stage1_decision(request, proposal_id):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    proposal = get_object_or_404(Proposals, proposal_id=proposal_id)

    stage1_reviews = Stage1Reviews.objects.filter(
        assignment__proposal=proposal,
        is_submitted=True
    )

    if stage1_reviews.count() == 0:
        return render(request, "p3/chair_stage1_decision.html", {
            "proposal": proposal,
            "reviews": stage1_reviews,
            "error": "No Stage 1 reviews submitted yet.",
            "form": None
        })

    avg_score = stage1_reviews.aggregate(avg=Avg("total_percentage"))["avg"]

    if request.method == "POST":
        form = Stage1DecisionForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["decision"]
            remarks = form.cleaned_data["remarks"]

            proposal.stage1_decision = decision
            proposal.stage1_remarks = remarks
            proposal.stage1_decision_date = timezone.now()

            # Update proposal status based on stage 1 decision
            if decision == "ACCEPT":
                proposal.status = "ACCEPTED_NO_CORRECTIONS"
            elif decision == "REJECT":
                proposal.status = "STAGE_1_REJECTED"
            elif decision == "TENTATIVE":
                proposal.status = "REVISION_REQUESTED"
                proposal.revision_deadline = proposal.cycle.revision_duration_days

            proposal.save()

            Auditlogs.objects.create(
                actor_user=request.user,
                action_type="Stage1DecisionSet",
                target_entity="Proposals",
                target_id=proposal.proposal_id,
                details=decision,
                timestamp=timezone.now()
            )

            return redirect("p3_chair_report_proposal", proposal_id=proposal.proposal_id)
    else:
        form = Stage1DecisionForm()

    return render(request, "p3/chair_stage1_decision.html", {
        "proposal": proposal,
        "reviews": stage1_reviews,
        "avg_score": avg_score,
        "form": form,
        "error": None
    })


# ----------------------------------------
# FINAL DECISION (STAGE 2)
# ----------------------------------------
@login_required
def chair_final_decision(request, proposal_id):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    proposal = get_object_or_404(Proposals, proposal_id=proposal_id)

    if not proposal.stage1_decision:
        messages.error(request, "Stage 1 decision must be completed before Stage 2.")
        return redirect("p3_chair_stage1_decision", proposal_id=proposal.proposal_id)

    if proposal.stage1_decision == "REJECT":
        messages.error(request, "This proposal was rejected in Stage 1. Final decision is not allowed.")
        return redirect("p3_chair_report_proposal", proposal_id=proposal.proposal_id)

    stage2_reviews = Stage2Reviews.objects.filter(assignment__proposal=proposal)
    documents = Proposaldocuments.objects.filter(proposal=proposal)

    if request.method == "POST":
        form = FinalDecisionForm(request.POST)
        if form.is_valid():
            final_decision = form.cleaned_data["final_decision"]
            amount = form.cleaned_data.get("final_grant_amount")
            remarks = form.cleaned_data.get("final_remarks")

            proposal.final_decision = final_decision
            proposal.final_grant_amount = amount
            proposal.final_remarks = remarks

            # FIX - update proposal status based on final decision
            if final_decision == "ACCEPTED":
                proposal.status = "FINAL_ACCEPTED"
            elif final_decision == "REJECTED":
                proposal.status = "FINAL_REJECTED"

            proposal.save()

            Auditlogs.objects.create(
                actor_user=request.user,
                action_type="FinalDecisionSet",
                target_entity="Proposals",
                target_id=proposal.proposal_id,
                details=final_decision,
                timestamp=timezone.now()
            )

            return redirect("p3_chair_report_proposal", proposal_id=proposal.proposal_id)
    else:
        form = FinalDecisionForm()

    return render(request, "p3/chair_final_decision.html", {
        "proposal": proposal,
        "stage2_reviews": stage2_reviews,
        "documents": documents,
        "form": form
    })


# ----------------------------------------
# REPORTS HOME
# ----------------------------------------
@login_required
def chair_reports_home(request):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    proposals = Proposals.objects.all().order_by("-proposal_id")

    return render(request, "p3/chair_reports_home.html", {
        "proposals": proposals
    })


# ----------------------------------------
# PROPOSAL REPORT
# ----------------------------------------
@login_required
def chair_report_proposal(request, proposal_id):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    proposal = get_object_or_404(Proposals, proposal_id=proposal_id)

    stage1_reviews = Stage1Reviews.objects.filter(assignment__proposal=proposal)
    stage2_reviews = Stage2Reviews.objects.filter(assignment__proposal=proposal)
    assignments = Reviewassignments.objects.filter(proposal=proposal)

    # FIX - show only latest version per document type
    from django.db.models import Max
    latest_ids = (
        Proposaldocuments.objects
        .filter(proposal=proposal)
        .values("document_type")
        .annotate(latest_id=Max("document_id"))
        .values_list("latest_id", flat=True)
    )
    documents = Proposaldocuments.objects.filter(document_id__in=latest_ids).order_by("document_type")

    logs = Auditlogs.objects.filter(
        target_entity="Proposals",
        target_id=proposal.proposal_id
    ).order_by("-timestamp")

    return render(request, "p3/chair_report_proposal.html", {
        "proposal": proposal,
        "stage1_reviews": stage1_reviews,
        "stage2_reviews": stage2_reviews,
        "assignments": assignments,
        "documents": documents,
        "logs": logs
    })


@login_required
def chair_report_proposal_pdf(request, proposal_id):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    proposal = get_object_or_404(
        Proposals.objects.select_related("pi_user", "department", "department__school", "cycle"),
        proposal_id=proposal_id
    )
    stage1_reviews = Stage1Reviews.objects.filter(
        assignment__proposal=proposal
    ).select_related("assignment__reviewer__user")
    stage2_reviews = Stage2Reviews.objects.filter(
        assignment__proposal=proposal
    ).select_related("assignment__reviewer__user")
    assignments = Reviewassignments.objects.filter(proposal=proposal).select_related("reviewer__user")
    documents = Proposaldocuments.objects.filter(proposal=proposal).order_by("document_type", "-version")
    logs = Auditlogs.objects.filter(
        target_entity="Proposals",
        target_id=proposal.proposal_id
    ).order_by("-timestamp")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="proposal_report_{proposal.proposal_id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    def styled_table(data, col_widths=None):
        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#eef2ff")]),
        ]))
        return table

    story.append(Paragraph(f"Proposal Report: {proposal.title}", styles["Title"]))
    story.append(Spacer(1, 12))
    summary_data = [
        ["Field", "Value"],
        ["Proposal ID", str(proposal.proposal_id)],
        ["PI User", getattr(proposal.pi_user, "username", str(proposal.pi_user))],
        ["School", getattr(getattr(proposal.department, "school", None), "school_name", "N/A")],
        ["Department", getattr(proposal.department, "department_name", "N/A")],
        ["Cycle", getattr(proposal.cycle, "cycle_name", "N/A")],
        ["Status", proposal.status or ""],
        ["Stage 1 Decision", proposal.stage1_decision or ""],
        ["Final Decision", proposal.final_decision or ""],
        ["Final Grant Amount", str(proposal.final_grant_amount or "")],
    ]
    story.append(styled_table(summary_data, [150, 340]))
    story.append(Spacer(1, 18))

    assignment_data = [["Assignment ID", "Reviewer", "Acceptance Status", "Active"]]
    for assignment in assignments:
        assignment_data.append([
            str(assignment.assignment_id),
            getattr(getattr(assignment, "reviewer", None).user, "username", "") if getattr(assignment, "reviewer", None) else "",
            assignment.acceptance_status or "",
            str(assignment.is_active),
        ])
    story.append(Paragraph("Review Assignments", styles["Heading2"]))
    story.append(styled_table(assignment_data, [90, 170, 140, 90]))
    story.append(Spacer(1, 18))

    document_data = [["Document Type", "Version", "File Path"]]
    for doc_item in documents:
        document_data.append([doc_item.document_type, str(doc_item.version or ""), doc_item.file_path])
    story.append(Paragraph("Documents", styles["Heading2"]))
    story.append(styled_table(document_data, [110, 70, 310]))
    story.append(PageBreak())

    stage1_data = [[
        "Reviewer", "Orig.", "Clar.", "Lit.", "Meth.", "Impact", "Pub.", "Budget", "Time", "Total", "Submitted"
    ]]
    for review in stage1_reviews:
        stage1_data.append([
            getattr(getattr(review.assignment, "reviewer", None).user, "username", "") if getattr(review.assignment, "reviewer", None) else "",
            str(review.score_originality or ""),
            str(review.score_clarity or ""),
            str(review.score_lit_review or ""),
            str(review.score_methodology or ""),
            str(review.score_impact or ""),
            str(review.score_publication or ""),
            str(review.score_budget or ""),
            str(review.score_timeframe or ""),
            str(review.total_percentage or ""),
            str(review.is_submitted),
        ])
    story.append(Paragraph("Stage 1 Reviews", styles["Heading2"]))
    story.append(styled_table(stage1_data, [90, 36, 36, 36, 40, 40, 36, 42, 36, 42, 60]))
    story.append(Spacer(1, 18))

    stage2_data = [["Reviewer", "Concerns Addressed", "Recommendation", "Revised Score", "Comments"]]
    for review in stage2_reviews:
        stage2_data.append([
            getattr(getattr(review.assignment, "reviewer", None).user, "username", "") if getattr(review.assignment, "reviewer", None) else "",
            review.concerns_addressed or "",
            review.recommendation or "",
            str(review.revised_score or ""),
            review.comments or "",
        ])
    story.append(Paragraph("Stage 2 Reviews", styles["Heading2"]))
    story.append(styled_table(stage2_data, [90, 100, 90, 70, 190]))
    story.append(Spacer(1, 18))

    log_data = [["Timestamp", "Actor", "Action", "Details"]]
    for log in logs:
        log_data.append([
            str(log.timestamp),
            str(log.actor_user),
            log.action_type,
            log.details or "",
        ])
    story.append(Paragraph("Audit Logs", styles["Heading2"]))
    story.append(styled_table(log_data, [120, 90, 90, 220]))

    doc.build(story)
    return response


# ----------------------------------------
# AUDIT LOG PAGE
# ----------------------------------------
@login_required
def chair_auditlogs(request):
    if not is_chair(request.user):
        return HttpResponseForbidden("SRC Chair access only.")

    logs = Auditlogs.objects.all().order_by("-timestamp")

    action = request.GET.get("action_type")
    if action:
        logs = logs.filter(action_type=action)

    return render(request, "p3/chair_auditlogs.html", {
        "logs": logs
    })
