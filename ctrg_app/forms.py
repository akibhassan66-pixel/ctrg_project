from django import forms
from .models import Grantcycles

class GrantCycleForm(forms.ModelForm):
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
            'stage1_start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'stage1_end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'stage2_start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'stage2_end_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'acceptance_threshold': forms.NumberInput(attrs={'placeholder': '70'}),
            'revision_duration_days': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'max_reviewers_per_proposal': forms.NumberInput(attrs={'placeholder': '2'}),
        }
