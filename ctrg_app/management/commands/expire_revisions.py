"""
Management command: expire_revisions

Finds proposals in REVISION_REQUESTED status whose revision_deadline has passed
and marks them as FINAL_REJECTED, with an audit log entry.

Usage:
    python manage.py expire_revisions

For testing you can set a short revision_duration_days (e.g. 0) on the grant cycle
and set revision_deadline to a near future datetime directly in the DB,
then run this command to see the auto-reject fire.
"""

import datetime as _dt

from django.core.management.base import BaseCommand

from ctrg_app.models import Proposals, Auditlogs


def _naive(d):
    return d.replace(tzinfo=None) if d and getattr(d, 'tzinfo', None) else d


class Command(BaseCommand):
    help = 'Auto-reject proposals whose revision deadline has expired.'

    def handle(self, *args, **options):
        now = _dt.datetime.now()  # naive local time, matches how deadlines are stored

        all_pending = Proposals.objects.filter(status='REVISION_REQUESTED')
        expired = [p for p in all_pending if p.revision_deadline and _naive(p.revision_deadline) < now]

        count = len(expired)
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No expired revisions found.'))
            return

        for proposal in expired:
            proposal.status = 'FINAL_REJECTED'
            proposal.final_remarks = (
                f'Auto-rejected: revision deadline {proposal.revision_deadline} passed without submission.'
            )
            proposal.save(update_fields=['status', 'final_remarks'])

            from django.utils import timezone as tz
            Auditlogs.objects.create(
                actor_user=None,
                action_type='RevisionDeadlineExpired',
                target_entity='Proposals',
                target_id=proposal.proposal_id,
                details=f'Auto-rejected at {now}. Deadline was {_naive(proposal.revision_deadline)}.',
                timestamp=tz.now(),
            )

            self.stdout.write(
                self.style.WARNING(
                    f'  Auto-rejected proposal #{proposal.proposal_id} '
                    f'"{proposal.title}" (deadline: {proposal.revision_deadline})'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(f'Done. {count} proposal(s) auto-rejected.')
        )
