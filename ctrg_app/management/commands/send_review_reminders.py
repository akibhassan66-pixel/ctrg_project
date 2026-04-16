import datetime as _dt

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from ctrg_app.models import Auditlogs, Reviewassignments


REMINDER_ACTION = 'ReviewDeadlineReminderSent'
REMINDER_ENTITY = 'Reviewers'


def _naive(value):
    if value is None:
        return None
    if getattr(value, 'tzinfo', None):
        # Convert aware datetimes to project local time first, then compare as naive.
        return timezone.localtime(value).replace(tzinfo=None)
    return value


def _reminder_key(stage_name, proposal_id, due_dt):
    due_minute = due_dt.replace(second=0, microsecond=0)
    return f'{stage_name}|{proposal_id}|{due_minute.isoformat(timespec="minutes")}'


def _is_in_24h_window(due_dt, now, window_minutes):
    delta = due_dt - now
    lower = _dt.timedelta(hours=24)
    upper = lower + _dt.timedelta(minutes=window_minutes)
    return lower <= delta < upper


def _display_due(value):
    naive_value = _naive(value)
    if not naive_value:
        return 'N/A'
    return naive_value.strftime('%b %d, %Y %I:%M %p')


def _build_batches(assignments, now=None, window_minutes=1440):
    now = _naive(now or _dt.datetime.now())
    batches = {}

    for assignment in assignments:
        reviewer = getattr(assignment, 'reviewer', None)
        proposal = getattr(assignment, 'proposal', None)
        if not reviewer or not proposal:
            continue

        user = getattr(reviewer, 'user', None)
        email = getattr(user, 'email', '') or ''
        if not email:
            continue

        cycle = getattr(proposal, 'cycle', None)
        if not cycle:
            continue

        reviewer_id = getattr(reviewer, 'reviewer_id', None)
        if reviewer_id is None:
            continue

        batch = batches.setdefault(
            reviewer_id,
            {
                'reviewer_id': reviewer_id,
                'username': getattr(user, 'username', '') or email,
                'email': email,
                'stage1': [],
                'stage2': [],
            },
        )

        for stage_name, due_attr in (('stage1', 'stage1_end_date'), ('stage2', 'stage2_end_date')):
            due_value = _naive(getattr(cycle, due_attr, None))
            if due_value and _is_in_24h_window(due_value, now, window_minutes):
                batch[stage_name].append(
                    {
                        'proposal_id': getattr(proposal, 'proposal_id', ''),
                        'title': getattr(proposal, 'title', '') or '',
                        'unique_code': getattr(proposal, 'unique_code', '') or '',
                        'due': due_value,
                        'reminder_key': _reminder_key(stage_name, getattr(proposal, 'proposal_id', ''), due_value),
                    }
                )

    for batch in batches.values():
        batch['stage1'].sort(key=lambda item: (item['due'], item['title'], item['proposal_id']))
        batch['stage2'].sort(key=lambda item: (item['due'], item['title'], item['proposal_id']))

    return [batch for batch in batches.values() if batch['stage1'] or batch['stage2']]


def _compose_email(batch, stages_to_send):
    subject_parts = []
    if 'stage1' in stages_to_send:
        subject_parts.append('Stage 1')
    if 'stage2' in stages_to_send:
        subject_parts.append('Stage 2')

    if len(subject_parts) == 1:
        subject = f"CTRG Reminder: {subject_parts[0]} review deadline due tomorrow"
    else:
        subject = 'CTRG Reminder: Stage 1 and Stage 2 review deadlines due tomorrow'

    lines = [
        f"Dear {batch['username']},",
        '',
        'This is a reminder that the following review deadline(s) are due within one day:',
        '',
    ]

    for stage_name, stage_label in (('stage1', 'Stage 1'), ('stage2', 'Stage 2')):
        if stage_name not in stages_to_send:
            continue

        lines.append(f'{stage_label} review deadline(s):')
        for item in stages_to_send[stage_name]:
            ref = item['unique_code'] or f"#{item['proposal_id']}"
            lines.append(
                f"- {item['title']} ({ref}) - deadline: {_display_due(item['due'])}"
            )
        lines.append('')

    lines.extend([
        'Please submit your review as soon as possible before the deadline ends.',
        '',
        'Thank you,',
        'CTRG System',
    ])

    return subject, '\n'.join(lines)


class Command(BaseCommand):
    help = 'Send reminder emails to reviewers one day before Stage 1/Stage 2 deadlines.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--window-minutes',
            type=int,
            default=1440,
            help='Send reminders when deadline is between +24h and +24h + window (minutes).',
        )

    def handle(self, *args, **options):
        window_minutes = max(1, int(options.get('window_minutes') or 1440))
        now = timezone.localtime(timezone.now()).replace(tzinfo=None)

        assignments = (
            Reviewassignments.objects
            .filter(
                is_active=True,
                acceptance_status__in=['PENDING', 'ACCEPTED'],
                reviewer__is_active=True,
                reviewer__user__is_active=True,
            )
            .select_related('reviewer__user', 'proposal__cycle')
        )

        batches = _build_batches(assignments, now=now, window_minutes=window_minutes)
        if not batches:
            self.stdout.write(self.style.SUCCESS('No review deadline reminders are due in the configured 24-hour window.'))
            return

        sent_emails = 0
        sent_reminders = 0

        for batch in batches:
            stages_to_send = {}

            for stage_name in ('stage1', 'stage2'):
                items = batch[stage_name]
                if not items:
                    continue

                unsent_items = []
                for item in items:
                    already_sent = Auditlogs.objects.filter(
                        action_type=REMINDER_ACTION,
                        target_entity=REMINDER_ENTITY,
                        target_id=batch['reviewer_id'],
                        details=item['reminder_key'],
                    ).exists()
                    if not already_sent:
                        unsent_items.append(item)

                if not unsent_items:
                    continue

                stages_to_send[stage_name] = unsent_items

            if not stages_to_send:
                continue

            try:
                subject, body = _compose_email(batch, stages_to_send)
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[batch['email']],
                    fail_silently=False,
                )
            except Exception as exc:
                self.stdout.write(self.style.ERROR(
                    f"Failed to send reminder to {batch['email']}: {exc}"
                ))
                continue

            for stage_name, items in stages_to_send.items():
                for item in items:
                    Auditlogs.objects.create(
                        actor_user=None,
                        action_type=REMINDER_ACTION,
                        target_entity=REMINDER_ENTITY,
                        target_id=batch['reviewer_id'],
                        details=item['reminder_key'],
                        timestamp=timezone.now(),
                    )
                    sent_reminders += 1

            sent_emails += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sent reminder email to {batch['email']} for {', '.join(stages_to_send.keys())}."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Sent {sent_emails} reminder email(s) covering {sent_reminders} reminder item(s) '
                f'with a {window_minutes}-minute window.'
            )
        )


