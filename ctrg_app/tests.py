import datetime as _dt
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.test.utils import override_settings
from django.utils import timezone

from ctrg_app.management.commands.send_review_reminders import (
	_build_batches,
	_compose_email,
	_naive,
	_reminder_key,
)


class ReviewReminderHelperTests(SimpleTestCase):
	def setUp(self):
		self.now = _dt.datetime(2026, 4, 12, 10, 0)

	def test_build_batches_groups_stage1_and_stage2_due_within_minute_window(self):
		reviewer = SimpleNamespace(
			reviewer_id=7,
			user=SimpleNamespace(username='reviewer1', email='reviewer1@example.com'),
		)

		proposal1 = SimpleNamespace(
			proposal_id=101,
			title='AI for Health',
			unique_code='P101',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 13, 10, 30),
				stage2_end_date=_dt.datetime(2026, 4, 20, 15, 30),
			),
		)
		proposal2 = SimpleNamespace(
			proposal_id=102,
			title='Green Energy',
			unique_code='P102',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 18, 9, 0),
				stage2_end_date=_dt.datetime(2026, 4, 13, 10, 45),
			),
		)
		proposal3 = SimpleNamespace(
			proposal_id=103,
			title='Not Due Yet',
			unique_code='P103',
			cycle=SimpleNamespace(
				stage1_end_date=_dt.datetime(2026, 4, 13, 12, 0),
				stage2_end_date=_dt.datetime(2026, 4, 15, 12, 0),
			),
		)

		assignments = [
			SimpleNamespace(reviewer=reviewer, proposal=proposal1),
			SimpleNamespace(reviewer=reviewer, proposal=proposal2),
			SimpleNamespace(reviewer=reviewer, proposal=proposal3),
		]

		batches = _build_batches(assignments, now=self.now, window_minutes=60)

		self.assertEqual(len(batches), 1)
		batch = batches[0]
		self.assertEqual(batch['reviewer_id'], 7)
		self.assertEqual(batch['email'], 'reviewer1@example.com')
		self.assertEqual([item['proposal_id'] for item in batch['stage1']], [101])
		self.assertEqual([item['proposal_id'] for item in batch['stage2']], [102])
		self.assertTrue(batch['stage1'][0]['reminder_key'].startswith('stage1|101|2026-04-13T10:30'))

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

		self.assertEqual(subject, 'CTRG Reminder: Stage 1 and Stage 2 review deadlines due tomorrow')
		self.assertIn('Dear reviewer1,', body)
		self.assertIn('Stage 1 review deadline(s):', body)
		self.assertIn('Stage 2 review deadline(s):', body)
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

