from django import forms
from django.utils import timezone
from .models import Grantcycles

class GrantCycleForm(forms.ModelForm):
    DATETIME_FIELDS = (
        'stage1_start_date',
        'stage1_end_date',
        'revision_duration_days',
        'stage2_start_date',
        'stage2_end_date',
    )

    class Meta:
        model = Grantcycles
        fields = [
            'cycle_name',
            'year',
            'school',
            'stage1_start_date',
            'stage1_end_date',
            'revision_duration_days',
            'stage2_start_date',
            'stage2_end_date',
            'acceptance_threshold',
            'max_reviewers_per_proposal'
        ]

        labels = {
            'school': 'School',
        }

        widgets = {
            'stage1_start_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'stage1_end_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'stage2_start_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'stage2_end_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'acceptance_threshold': forms.NumberInput(attrs={'placeholder': '70'}),
            'revision_duration_days': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'max_reviewers_per_proposal': forms.NumberInput(attrs={'placeholder': '2'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.DATETIME_FIELDS:
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.DATETIME_FIELDS:
            value = cleaned_data.get(field_name)
            if value is None:
                continue
            if not timezone.is_naive(value):
                value = timezone.make_naive(value, timezone.get_current_timezone())
            cleaned_data[field_name] = value
        return cleaned_data
