# p3_urls.py
from django.urls import path
from . import p3_views_pi, p3_views_chair

urlpatterns = [
    # PI
    path('pi/dashboard/', p3_views_pi.pi_dashboard, name='p3_pi_dashboard'),
    path('pi/proposals/create/', p3_views_pi.pi_submit_proposal, name='p3_pi_submit_proposal'),
    path('pi/proposals/<int:proposal_id>/', p3_views_pi.pi_proposal_detail, name='p3_pi_proposal_detail'),
    path('pi/proposals/<int:proposal_id>/revision/', p3_views_pi.pi_revision_submit, name='p3_pi_revision_submit'),
path('pi/proposals/<int:proposal_id>/reupload/<str:document_type>/', p3_views_pi.pi_reupload_file, name='p3_pi_reupload_file'),
    # Chair (Decisions)
    path('chair/proposals/<int:proposal_id>/stage1-decision/', p3_views_chair.chair_stage1_decision, name='p3_chair_stage1_decision'),
    path('chair/proposals/<int:proposal_id>/final-decision/', p3_views_chair.chair_final_decision, name='p3_chair_final_decision'),

    # Chair (Reports + Audit)
    path('chair/reports/', p3_views_chair.chair_reports_home, name='p3_chair_reports_home'),
    path('chair/reports/proposal/<int:proposal_id>/', p3_views_chair.chair_report_proposal, name='p3_chair_report_proposal'),
    path('chair/reports/proposal/<int:proposal_id>/pdf/', p3_views_chair.chair_report_proposal_pdf, name='p3_chair_report_proposal_pdf'),
    path('chair/auditlogs/', p3_views_chair.chair_auditlogs, name='p3_chair_auditlogs'),
]
