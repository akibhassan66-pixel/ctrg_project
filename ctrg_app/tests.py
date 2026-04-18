import datetime as _dt
import os
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test import RequestFactory
from django.test.utils import override_settings
from django.utils import timezone

from ctrg_app.management.commands.send_review_reminders import (
	_build_batches,
	_compose_email,
	_naive,
	_reminder_key,
)
from ctrg_app.stage1_scoring import calculate_stage1_total
from ctrg_app.views import build_assignment_email, send_assignment_email


class ReviewReminderHelperTests(SimpleTestCase):
	def setUp(self):
		self.now = _dt.datetime(2026, 4, 12, 10, 0)

	def test_build_batches_includes_only_pending_stage_work_due_within_next_window(self):
		reviewer = SimpleNamespace(
			reviewer_id=7,
			user=SimpleNamespace(username='reviewer1', email='reviewer1@example.com'),
		)

		proposal1 = SimpleNamespace(
			proposal_id=101,
			title='AI for Health',
			unique_code='P101',
			status='UNDER_STAGE_1_REVIEW',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 12, 16, 0),
				stage2_end_date=_dt.datetime(2026, 4, 20, 15, 30),
			),
		)
		proposal2 = SimpleNamespace(
			proposal_id=102,
			title='Green Energy',
			unique_code='P102',
			status='UNDER_STAGE_2_REVIEW',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 5, 9, 0),
				stage2_end_date=_dt.datetime(2026, 4, 12, 18, 45),
			),
		)
		proposal3 = SimpleNamespace(
			proposal_id=103,
			title='Already Submitted',
			unique_code='P103',
			status='UNDER_STAGE_1_REVIEW',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 12, 15, 0),
				stage2_end_date=_dt.datetime(2026, 4, 15, 12, 0),
			),
		)
		proposal4 = SimpleNamespace(
			proposal_id=104,
			title='Stage 2 Blocked',
			unique_code='P104',
			status='UNDER_STAGE_2_REVIEW',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 10, 12, 0),
				stage2_end_date=_dt.datetime(2026, 4, 12, 14, 0),
			),
		)
		proposal5 = SimpleNamespace(
			proposal_id=105,
			title='Outside Window',
			unique_code='P105',
			status='UNDER_STAGE_1_REVIEW',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 13, 11, 30),
				stage2_end_date=_dt.datetime(2026, 4, 15, 12, 0),
			),
		)

		assignments = [
			SimpleNamespace(reviewer=reviewer, proposal=proposal1, stage1_submitted=False, stage2_submitted=False),
			SimpleNamespace(reviewer=reviewer, proposal=proposal2, stage1_submitted=True, stage2_submitted=False),
			SimpleNamespace(reviewer=reviewer, proposal=proposal3, stage1_submitted=True, stage2_submitted=False),
			SimpleNamespace(reviewer=reviewer, proposal=proposal4, stage1_submitted=False, stage2_submitted=False),
			SimpleNamespace(reviewer=reviewer, proposal=proposal5, stage1_submitted=False, stage2_submitted=False),
		]

		batches = _build_batches(assignments, now=self.now, window_minutes=1440)

		self.assertEqual(len(batches), 1)
		batch = batches[0]
		self.assertEqual(batch['reviewer_id'], 7)
		self.assertEqual(batch['email'], 'reviewer1@example.com')
		self.assertEqual([item['proposal_id'] for item in batch['stage1']], [101])
		self.assertEqual([item['proposal_id'] for item in batch['stage2']], [102])
		self.assertTrue(batch['stage1'][0]['reminder_key'].startswith('stage1|101|2026-04-12T16:00'))

	def test_build_batches_skips_proposals_outside_active_stage_status(self):
		reviewer = SimpleNamespace(
			reviewer_id=7,
			user=SimpleNamespace(username='reviewer1', email='reviewer1@example.com'),
		)
		assignments = [
			SimpleNamespace(
				reviewer=reviewer,
				proposal=SimpleNamespace(
					proposal_id=201,
					title='Revision Requested',
					unique_code='P201',
					status='REVISION_REQUESTED',
					cycle=SimpleNamespace(
						stage1_end_date=_dt.datetime(2026, 4, 12, 18, 0),
						stage2_end_date=_dt.datetime(2026, 4, 12, 19, 0),
					),
				),
				stage1_submitted=False,
				stage2_submitted=False,
			),
			SimpleNamespace(
				reviewer=reviewer,
				proposal=SimpleNamespace(
					proposal_id=202,
					title='Final Accepted',
					unique_code='P202',
					status='FINAL_ACCEPTED',
					cycle=SimpleNamespace(
						stage1_end_date=_dt.datetime(2026, 4, 12, 18, 0),
						stage2_end_date=_dt.datetime(2026, 4, 12, 19, 0),
					),
				),
				stage1_submitted=True,
				stage2_submitted=False,
			),
		]

		self.assertEqual(_build_batches(assignments, now=self.now, window_minutes=1440), [])

	def test_compose_email_includes_both_stage_sections(self):
		batch = {
			'username': 'reviewer1',
			'stage1': [
				{
					'proposal_id': 101,
					'title': 'AI for Health',
					'unique_code': 'P101',
					'due': _dt.datetime(2026, 4, 13, 15, 30),
				}
			],
			'stage2': [
				{
					'proposal_id': 102,
					'title': 'Green Energy',
					'unique_code': 'P102',
					'due': _dt.datetime(2026, 4, 13, 16, 45),
				}
			],
		}

		subject, body = _compose_email(batch, {'stage1': batch['stage1'], 'stage2': batch['stage2']})

		self.assertEqual(subject, 'CTRG Reminder: Stage 1 and Stage 2 review deadlines due within 24 hours')
		self.assertIn('Dear reviewer1,', body)
		self.assertIn('Stage 1 review deadline(s):', body)
		self.assertIn('Stage 2 review deadline(s):', body)
		self.assertIn('within the next 24 hours', body)
		self.assertIn('AI for Health (P101)', body)
		self.assertIn('Green Energy (P102)', body)

	def test_reminder_key_is_stable(self):
		self.assertEqual(
			_reminder_key('stage1', 101, _dt.datetime(2026, 4, 13, 10, 30, 55)),
			'stage1|101|2026-04-13T10:30',
		)

	@override_settings(TIME_ZONE='Asia/Dhaka', USE_TZ=True)
	def test_naive_converts_aware_to_local_time(self):
		tz = timezone.get_fixed_timezone(0)
		aware_utc = _dt.datetime(2026, 4, 13, 10, 30, tzinfo=tz)
		local_naive = _naive(aware_utc)
		self.assertEqual(local_naive, _dt.datetime(2026, 4, 13, 16, 30))


class AssignmentEmailHelperTests(SimpleTestCase):
	def setUp(self):
		self.factory = RequestFactory()
		self.request = self.factory.get("/", HTTP_HOST="127.0.0.1:8000")
		self.reviewer = SimpleNamespace(
			user=SimpleNamespace(username="reviewer1", email="reviewer1@example.com"),
		)
		self.proposal = SimpleNamespace(title="Street Food Business Model")
		self.assignment = SimpleNamespace(assignment_id=42)

	def test_build_assignment_email_uses_absolute_response_url(self):
		subject, body, html_body = build_assignment_email(
			self.request,
			self.reviewer,
			self.proposal,
			self.assignment,
		)

		self.assertEqual(subject, "New Proposal Assignment - CTRG System")
		self.assertIn("Street Food Business Model", body)
		self.assertIn("http://127.0.0.1:8000/reviewer/assignments/42/respond/", body)
		self.assertIn("http://127.0.0.1:8000/reviewer/assignments/42/respond/", html_body)

	@override_settings(
		EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
		DEFAULT_FROM_EMAIL="admin@example.com",
	)
	@patch.dict(os.environ, {"BREVO_API_KEY": "", "RESEND_API_KEY": ""})
	def test_send_assignment_email_reports_console_backend_as_local_only(self):
		sent, message = send_assignment_email(
			self.request,
			self.reviewer,
			self.proposal,
			self.assignment,
		)

		self.assertFalse(sent)
		self.assertIn("local-only email backend", message)

	def test_send_assignment_email_requires_reviewer_email(self):
		reviewer_without_email = SimpleNamespace(
			user=SimpleNamespace(username="reviewer1", email=""),
		)

		sent, message = send_assignment_email(
			self.request,
			reviewer_without_email,
			self.proposal,
			self.assignment,
		)

		self.assertFalse(sent)
		self.assertIn("has no email address", message)


class Stage1ScoringTests(SimpleTestCase):
	def test_calculate_stage1_total_returns_sum_as_decimal(self):
		total = calculate_stage1_total(15, 15, 15, 15, 15, 10, 10, 5)
		self.assertEqual(str(total), "100.00")

