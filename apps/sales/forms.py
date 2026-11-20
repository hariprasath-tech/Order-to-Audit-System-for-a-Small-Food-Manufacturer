"""
Forms for Sales Order Entry.
"""

from django import forms
from django.utils import timezone

from apps.masters.models import Customer


class SalesOrderCreateForm(forms.Form):
    """
    Form validating header and payload for dynamic multi-line order submissions.
    """

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(is_active=True).order_by("name"),
        required=True,
        empty_label="Select a wholesale customer...",
        widget=forms.Select(
            attrs={
                "class": "w-full px-3 py-2 text-sm bg-bg border border-line rounded-lg text-ink focus:ring-2 focus:ring-brand focus:border-brand",
            }
        ),
    )
    order_date = forms.DateField(
        required=False,
        initial=timezone.now,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "w-full px-3 py-2 text-sm bg-bg border border-line rounded-lg text-ink focus:ring-2 focus:ring-brand focus:border-brand",
            }
        ),
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "Optional delivery notes or customer special requests...",
                "class": "w-full px-3 py-2 text-sm bg-bg border border-line rounded-lg text-ink focus:ring-2 focus:ring-brand focus:border-brand resize-none",
            }
        ),
    )
    action = forms.ChoiceField(
        choices=[("draft", "Save Draft"), ("submit", "Submit for Verification")],
        initial="draft",
        required=False,
    )

    def clean_order_date(self):
        d = self.cleaned_data.get("order_date")
        if not d:
            return timezone.now().date()
        return d
