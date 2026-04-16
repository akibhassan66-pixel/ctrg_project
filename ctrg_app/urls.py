# from django.urls import path, include
# from . import views
#
# urlpatterns = [
#     path('', views.login_view, name='login'),
#     path('signup/', views.signup_view, name='signup'),
#     path('logout/', views.logout_view, name='logout'),
#     path('', include('ctrg_app.p3_urls')),
#     path('dashboard/', views.dashboard, name='dashboard'),
#     # Dashboards
#     path('chair/dashboard/', views.chair_dashboard, name='chair_dashboard'),
#     path('reviewer/dashboard/', views.reviewer_dashboard, name='reviewer_dashboard'),
#     path('pi/dashboard/', views.pi_dashboard, name='pi_dashboard'),
#     path('chair/reviewers/', views.reviewer_list, name='reviewer_list'),
#     path('chair/reviewers/add/', views.create_reviewer, name='create_reviewer'),
#     path('chair/create-cycle/', views.create_grant_cycle, name='create_cycle'),
#
#     path('chair/cycles/', views.cycle_list, name='cycle_list'),
#     path('chair/reviewers/<int:reviewer_id>/edit/', views.edit_reviewer, name='edit_reviewer'),
#     path('chair/reviewers/<int:reviewer_id>/deactivate/', views.deactivate_reviewer, name='deactivate_reviewer'),
#     path('chair/cycles/<int:cycle_id>/edit/', views.edit_grant_cycle, name='edit_cycle'),
#     # Person 2: proposal + reviewer flow
#     path('proposals/', views.proposal_list, name='proposal_list'),
#     path('proposals/<int:proposal_id>/', views.proposal_detail, name='proposal_detail'),
#     path('proposals/<int:proposal_id>/assign/', views.assign_reviewer, name='assign_reviewer'),
#     path('review/stage1/<int:assignment_id>/', views.stage1_review, name='stage1_review'),
#     path('review/stage2/<int:assignment_id>/', views.stage2_review, name='stage2_review'),
#
#     # p3

# ]

from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Chair
    path('chair/dashboard/', views.chair_dashboard, name='chair_dashboard'),
    path('chair/reviewers/', views.reviewer_list, name='reviewer_list'),
    path('chair/reviewers/email/', views.email_reviewers, name='email_reviewers'),
    path('chair/reviewers/add/', views.create_reviewer, name='create_reviewer'),
    path('chair/reviewers/<int:reviewer_id>/', views.reviewer_detail, name='reviewer_detail'),
    path('chair/reviewers/<int:reviewer_id>/edit/', views.edit_reviewer, name='edit_reviewer'),
    path('chair/reviewers/<int:reviewer_id>/deactivate/', views.deactivate_reviewer, name='deactivate_reviewer'),
    path('chair/create-cycle/', views.create_grant_cycle, name='create_cycle'),
    path('chair/cycles/', views.cycle_list, name='cycle_list'),
    path('chair/cycles/<int:cycle_id>/edit/', views.edit_grant_cycle, name='edit_cycle'),
    path('chair/cycles/<int:cycle_id>/proposals/', views.proposals_by_cycle, name='proposals_by_cycle'),
    # Reviewer
    path('reviewer/dashboard/', views.reviewer_dashboard, name='reviewer_dashboard'),
path('reviewer/assignments/<int:assignment_id>/respond/', views.respond_to_assignment, name='respond_to_assignment'),
    # Person 2: proposal + reviewer flow
    path('proposals/', views.proposal_list, name='proposal_list'),
    path('proposals/<int:proposal_id>/', views.proposal_detail, name='proposal_detail'),
    path('proposals/<int:proposal_id>/assign/', views.assign_reviewer, name='assign_reviewer'),
    path('review/stage1/<int:assignment_id>/', views.stage1_review, name='stage1_review'),
    path('review/stage2/<int:assignment_id>/', views.stage2_review, name='stage2_review'),
    path('review/stage1/<int:assignment_id>/result/', views.stage1_review_result, name='stage1_review_result'),
    path('review/stage2/<int:assignment_id>/result/', views.stage2_review_result, name='stage2_review_result'),

    # Person 3 URLs (PI + Chair decisions + Reports)
    path('', include('ctrg_app.p3_urls')),

    path("chair/reviewers/download-excel/", views.export_reviewers_excel_one_row, name="export_reviewers_excel_one_row"),
    path("assignments/<int:assignment_id>/deactivate/", views.deactivate_assignment, name="deactivate_assignment"),
]
