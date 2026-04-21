# import uuid
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect, get_object_or_404
# from django.http import HttpResponseForbidden
# from django.utils import timezone
# from django.contrib import messages
#
# from .models import (
#     Proposals,
#     Proposaldocuments,
#     Auditlogs,
#     Departments,
#     Grantcycles,
#     Stage1Reviews,
#     Reviewers,
#     SrcChairs
# )
#
# from .p3_forms import ProposalSubmitForm, RevisionSubmitForm
#
#
# # ---------------------------
# # Role helpers
# # ---------------------------
# def is_chair(user):
#     return SrcChairs.objects.filter(user=user, is_active=1).exists()
#
# def is_reviewer(user):
#     return Reviewers.objects.filter(user=user, is_active=1).exists()
#
# def is_pi(user):
#     return (not is_chair(user)) and (not is_reviewer(user))
#
#
# # ---------------------------
# # PI Dashboard
# # ---------------------------
# @login_required
# def pi_dashboard(request):
#     if not is_pi(request.user):
#         return HttpResponseForbidden("PI access only.")
#
#     proposals = Proposals.objects.filter(pi_user=request.user).order_by("-proposal_id")
#     return render(request, "p3/pi_dashboard.html", {"proposals": proposals})
#
#
# # ---------------------------
# # PI Submit Proposal
# # ---------------------------
# @login_required
# def pi_submit_proposal(request):
#     if not is_pi(request.user):
#         return HttpResponseForbidden("PI access only.")
#
#     if request.method == "POST":
#         form = ProposalSubmitForm(request.POST, request.FILES)
#         if form.is_valid():
#             dept = form.cleaned_data["department"]
#
#             cycle = Grantcycles.objects.order_by("-cycle_id").first()
#             if not cycle:
#                 messages.error(request, "No grant cycle found. Please ask SRC Chair to create a cycle first.")
#                 return redirect("p3_pi_submit_proposal")
#
#             proposal = Proposals.objects.create(
#                 title=form.cleaned_data["title"],
#                 department=dept,
#                 pi_user=request.user,
#                 co_investigators=form.cleaned_data["co_investigators"],
#                 fund_requested=form.cleaned_data["fund_requested"],
#                 cycle=cycle,
#                 status="SUBMITTED",
#                 unique_code=f"CTRG-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
#             )
#
#             Proposaldocuments.objects.create(
#                 proposal=proposal,
#                 document_type="ORIGINAL",
#                 file_path=request.FILES["proposal_file"].name,
#                 uploaded_at=timezone.now(),
#                 version=1
#             )
#
#             Proposaldocuments.objects.create(
#                 proposal=proposal,
#                 document_type="TEMPLATE",
#                 file_path=request.FILES["application_template_file"].name,
#                 uploaded_at=timezone.now(),
#                 version=1
#             )
#
#             Auditlogs.objects.create(
#                 actor_user=request.user,
#                 action_type="ProposalSubmitted",
#                 target_entity="Proposals",
#                 target_id=proposal.proposal_id,
#                 details="Initial submission",
#                 timestamp=timezone.now()
#             )
#
#             return redirect("p3_pi_proposal_detail", proposal_id=proposal.proposal_id)
#     else:
#         initial_data = {"email": request.user.email}
#         form = ProposalSubmitForm(initial=initial_data)
#
#     return render(request, "p3/pi_submit_proposal.html", {
#         "form": form,
#         "pi_name": request.user.get_full_name() or request.user.username,
#         "pi_email": request.user.email
#     })
#
#
# # ---------------------------
# # PI Proposal Detail
# # ---------------------------
# @login_required
# def pi_proposal_detail(request, proposal_id):
#     if not is_pi(request.user):
#         return HttpResponseForbidden("PI access only.")
#
#     proposal = get_object_or_404(Proposals, proposal_id=proposal_id, pi_user=request.user)
#     docs = Proposaldocuments.objects.filter(proposal=proposal).order_by("-uploaded_at")
#
#     return render(request, "p3/pi_proposal_detail.html", {"proposal": proposal, "docs": docs})
#
#
# # ---------------------------
# # PI Revision Submission
# # ---------------------------
# @login_required
# def pi_revision_submit(request, proposal_id):
#     if not is_pi(request.user):
#         return HttpResponseForbidden("PI access only.")
#
#     proposal = get_object_or_404(Proposals, proposal_id=proposal_id, pi_user=request.user)
#
#     if proposal.status not in ("REVISION_REQUESTED", "TENTATIVELY_ACCEPTED"):
#         return HttpResponseForbidden("Revision not allowed for this proposal status.")
#
#     stage1_reviews = Stage1Reviews.objects.filter(
#         assignment__proposal=proposal,
#         is_submitted=1
#     )
#
#     if request.method == "POST":
#         form = RevisionSubmitForm(request.POST, request.FILES)
#         if form.is_valid():
#             Proposaldocuments.objects.create(
#                 proposal=proposal,
#                 document_type="REVISED",
#                 file_path=form.cleaned_data["revised_proposal_file"].name,
#                 uploaded_at=timezone.now(),
#                 version=1
#             )
#
#             if form.cleaned_data.get("response_to_reviewers_file"):
#                 Proposaldocuments.objects.create(
#                     proposal=proposal,
#                     document_type="RESPONSE",
#                     file_path=form.cleaned_data["response_to_reviewers_file"].name,
#                     uploaded_at=timezone.now(),
#                     version=1
#                 )
#
#             proposal.status = "REVISED_PROPOSAL_SUBMITTED"
#             proposal.save(update_fields=["status"])
#
#             Auditlogs.objects.create(
#                 actor_user=request.user,
#                 action_type="RevisionSubmitted",
#                 target_entity="Proposals",
#                 target_id=proposal.proposal_id,
#                 details="Revision uploaded",
#                 timestamp=timezone.now()
#             )
#
#             return redirect("p3_pi_proposal_detail", proposal_id=proposal.proposal_id)
#     else:
#         form = RevisionSubmitForm()
#
#     return render(request, "p3/pi_revision_submit.html", {
#         "proposal": proposal,
#         "form": form,
#         "stage1_reviews": stage1_reviews
#     })

import uuid
import os
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.utils import timezone
from django.contrib import messages
from django.db.models import Max
from .cycle_activation import get_active_cycle_id_for_school, get_latest_active_cycle_entry
from .models import (
    Proposals, Proposaldocuments, Auditlogs,
    Departments, Grantcycles, Stage1Reviews, Reviewers, SrcChairs
)
from .p3_forms import ProposalSubmitForm, RevisionSubmitForm


def is_chair(user):
    return SrcChairs.objects.filter(user=user, is_active=True).exists()

def is_reviewer(user):
    return Reviewers.objects.filter(user=user, is_active=True).exists()

def is_pi(user):
    return user.is_authenticated


def get_pi_school(user, proposals=None):
    department = getattr(user, "department", None)
    school = getattr(department, "school", None)
    if school:
        return school

    proposals = proposals or []
    for proposal in proposals:
        proposal_department = getattr(proposal, "department", None)
        proposal_school = getattr(proposal_department, "school", None)
        if proposal_school:
            return proposal_school

    return None


def save_uploaded_file(file, proposal_id, subfolder=""):
    folder = os.path.join(settings.MEDIA_ROOT, "proposals", str(proposal_id), subfolder)
    os.makedirs(folder, exist_ok=True)
    clean_name = file.name.replace(" ", "_").replace("(", "").replace(")", "")
    filename = f"{uuid.uuid4().hex[:8]}_{clean_name}"
    full_path = os.path.join(folder, filename)
    with open(full_path, 'wb+') as dest:
        for chunk in file.chunks():
            dest.write(chunk)
    return os.path.join("proposals", str(proposal_id), subfolder, filename).replace("\\", "/")


def delete_old_file(file_path):
    """Delete old file from disk if it exists."""
    if file_path:
        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if os.path.exists(full_path):
            os.remove(full_path)


@login_required
def pi_dashboard(request):
    if not is_pi(request.user):
        return HttpResponseForbidden("PI access only.")
    proposals = list(
        Proposals.objects
        .filter(pi_user=request.user)
        .select_related("cycle", "department__school")
        .order_by("-proposal_id")
    )
    school = get_pi_school(request.user, proposals=proposals)
    active_cycle = None
    active_cycle_school = None

    if school and getattr(school, "school_id", None):
        active_cycle_id = get_active_cycle_id_for_school(school.school_id)
        if active_cycle_id:
            active_cycle = (
                Grantcycles.objects
                .select_related("school")
                .filter(cycle_id=active_cycle_id, school=school)
                .first()
            )
            active_cycle_school = getattr(active_cycle, "school", None)

    if not active_cycle:
        latest_active = get_latest_active_cycle_entry()
        if latest_active:
            active_cycle = (
                Grantcycles.objects
                .select_related("school")
                .filter(
                    cycle_id=latest_active["cycle_id"],
                    school_id=latest_active["school_id"],
                )
                .first()
            )
            active_cycle_school = getattr(active_cycle, "school", None)

    return render(request, "p3/pi_dashboard.html", {
        "proposals": proposals,
        "pi_school": school,
        "active_cycle": active_cycle,
        "active_cycle_school": active_cycle_school,
    })


@login_required
def pi_submit_proposal(request):
    if not is_pi(request.user):
        return HttpResponseForbidden("PI access only.")

    if request.method == "POST":
        form = ProposalSubmitForm(request.POST, request.FILES)
        if form.is_valid():
            dept = form.cleaned_data["department"]
            school = getattr(dept, "school", None)
            if school is None:
                form.add_error("department", "The selected department is not assigned to a school.")
            else:
                active_cycle_id = get_active_cycle_id_for_school(getattr(school, "school_id", None))
                cycle = (
                    Grantcycles.objects
                    .filter(cycle_id=active_cycle_id, school=school)
                    .first()
                )
                if not cycle:
                    form.add_error(
                        None,
                        f"No active grant cycle is set for {school.school_name}. Please ask the SRC Chair to choose one.",
                    )
                else:
                    proposal = Proposals.objects.create(
                        title=form.cleaned_data["title"],
                        department=dept,
                        pi_user=request.user,
                        co_investigators=form.cleaned_data["co_investigators"],
                        fund_requested=form.cleaned_data["fund_requested"],
                        cycle=cycle,
                        status="SUBMITTED",
                        unique_code=f"CTRG-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                    )

                    # Save proposal file
                    proposal_file = request.FILES["proposal_file"]
                    proposal_path = save_uploaded_file(proposal_file, proposal.proposal_id, "original")
                    Proposaldocuments.objects.create(
                        proposal=proposal,
                        document_type="ORIGINAL",
                        file_path=proposal_path,
                        uploaded_at=timezone.now(),
                        version=1
                    )

                    # Save application template file
                    template_file = request.FILES["application_template_file"]
                    template_path = save_uploaded_file(template_file, proposal.proposal_id, "template")
                    Proposaldocuments.objects.create(
                        proposal=proposal,
                        document_type="TEMPLATE",
                        file_path=template_path,
                        uploaded_at=timezone.now(),
                        version=1
                    )

                    Auditlogs.objects.create(
                        actor_user=request.user,
                        action_type="ProposalSubmitted",
                        target_entity="Proposals",
                        target_id=proposal.proposal_id,
                        details="Initial submission",
                        timestamp=timezone.now()
                    )

                    return redirect("p3_pi_proposal_detail", proposal_id=proposal.proposal_id)
    else:
        form = ProposalSubmitForm(initial={"email": request.user.email})

    return render(request, "p3/pi_submit_proposal.html", {
        "form": form,
        "pi_name": request.user.get_full_name() or request.user.username,
        "pi_email": request.user.email
    })

@login_required
def pi_reupload_file(request, proposal_id, document_type):
    if not is_pi(request.user):
        return HttpResponseForbidden("PI access only.")

    proposal = get_object_or_404(Proposals, proposal_id=proposal_id, pi_user=request.user)

    if request.method == "POST":
        file = request.FILES.get("new_file")
        if not file:
            messages.error(request, "Please select a file.")
            return redirect("p3_pi_proposal_detail", proposal_id=proposal_id)

        # Delete old file from disk
        old_doc = (
            Proposaldocuments.objects
            .filter(proposal=proposal, document_type=document_type)
            .order_by("-document_id")
            .first()
        )
        if old_doc:
            delete_old_file(old_doc.file_path)

        # Get next version
        last_version = (
            Proposaldocuments.objects
            .filter(proposal=proposal, document_type=document_type)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        next_version = (last_version or 0) + 1

        # Save new file
        file_path = save_uploaded_file(file, proposal.proposal_id, document_type.lower())
        Proposaldocuments.objects.create(
            proposal=proposal,
            document_type=document_type,
            file_path=file_path,
            uploaded_at=timezone.now(),
            version=next_version
        )

        messages.success(request, f"{document_type} file updated successfully.")
        return redirect("p3_pi_proposal_detail", proposal_id=proposal_id)

    return render(request, "p3/pi_reupload_file.html", {
        "proposal": proposal,
        "document_type": document_type
    })
@login_required
def pi_proposal_detail(request, proposal_id):
    if not is_pi(request.user):
        return HttpResponseForbidden("PI access only.")
    proposal = get_object_or_404(Proposals, proposal_id=proposal_id, pi_user=request.user)

    from django.db.models import Max
    latest_ids = (
        Proposaldocuments.objects
        .filter(proposal=proposal)
        .values("document_type")
        .annotate(latest_id=Max("document_id"))
        .values_list("latest_id", flat=True)
    )
    docs = Proposaldocuments.objects.filter(document_id__in=latest_ids).order_by("document_type")

    # Check if any reviewer has submitted a stage 1 review
    review_submitted = Stage1Reviews.objects.filter(
        assignment__proposal=proposal,
        is_submitted=True
    ).exists()

    # Can only edit/reupload if SUBMITTED and no reviews yet
    can_edit = (proposal.status == "SUBMITTED") and (not review_submitted)

    return render(request, "p3/pi_proposal_detail.html", {
        "proposal": proposal,
        "docs": docs,
        "can_edit": can_edit
    })

@login_required
def pi_revision_submit(request, proposal_id):
    if not is_pi(request.user):
        return HttpResponseForbidden("PI access only.")

    proposal = get_object_or_404(Proposals, proposal_id=proposal_id, pi_user=request.user)

    if proposal.status not in ("REVISION_REQUESTED", "TENTATIVELY_ACCEPTED"):
        return HttpResponseForbidden("Revision not allowed for this proposal status.")

    # Enforce revision deadline in the configured Django timezone.
    def _naive(d):
        return d.replace(tzinfo=None) if d and getattr(d, 'tzinfo', None) else d
    now = timezone.localtime(timezone.now()).replace(tzinfo=None)
    if proposal.revision_deadline and now > _naive(proposal.revision_deadline):
        messages.error(request, "Revision deadline has passed. Submission is no longer accepted.")
        return redirect("p3_pi_proposal_detail", proposal_id=proposal.proposal_id)

    stage1_reviews = Stage1Reviews.objects.filter(
        assignment__proposal=proposal, is_submitted=True
    )

    if request.method == "POST":
        form = RevisionSubmitForm(request.POST, request.FILES)
        if form.is_valid():

            # Get next version number
            last_version = (
                Proposaldocuments.objects
                .filter(proposal=proposal, document_type="REVISED")
                .order_by("-version")
                .values_list("version", flat=True)
                .first()
            )
            next_version = (last_version or 0) + 1

            # Delete old REVISED file from disk before saving new one
            old_revised = (
                Proposaldocuments.objects
                .filter(proposal=proposal, document_type="REVISED")
                .order_by("-document_id")
                .first()
            )
            if old_revised:
                delete_old_file(old_revised.file_path)

            # Save new revised file
            revised_file = request.FILES["revised_proposal_file"]
            revised_path = save_uploaded_file(revised_file, proposal.proposal_id, "revised")
            Proposaldocuments.objects.create(
                proposal=proposal,
                document_type="REVISED",
                file_path=revised_path,
                uploaded_at=timezone.now(),
                version=next_version
            )

            # Delete old RESPONSE file from disk before saving new one
            if request.FILES.get("response_to_reviewers_file"):
                old_response = (
                    Proposaldocuments.objects
                    .filter(proposal=proposal, document_type="RESPONSE")
                    .order_by("-document_id")
                    .first()
                )
                if old_response:
                    delete_old_file(old_response.file_path)

                response_file = request.FILES["response_to_reviewers_file"]
                response_path = save_uploaded_file(response_file, proposal.proposal_id, "response")
                Proposaldocuments.objects.create(
                    proposal=proposal,
                    document_type="RESPONSE",
                    file_path=response_path,
                    uploaded_at=timezone.now(),
                    version=next_version
                )

            proposal.status = "UNDER_STAGE_2_REVIEW"
            proposal.save(update_fields=["status"])

            Auditlogs.objects.create(
                actor_user=request.user,
                action_type="RevisionSubmitted",
                target_entity="Proposals",
                target_id=proposal.proposal_id,
                details=f"Revision v{next_version} uploaded",
                timestamp=timezone.now()
            )

            return redirect("p3_pi_proposal_detail", proposal_id=proposal.proposal_id)
    else:
        form = RevisionSubmitForm()

    return render(request, "p3/pi_revision_submit.html", {
        "proposal": proposal,
        "form": form,
        "stage1_reviews": stage1_reviews
    })
