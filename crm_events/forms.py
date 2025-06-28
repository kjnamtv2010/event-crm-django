from django import forms

class EventRegistrationForm(forms.Form):
    name = forms.CharField(max_length=100, label="Your Name", required=False)
    email = forms.EmailField(label="Your Email", required=False)

    utm_source = forms.CharField(required=False, widget=forms.HiddenInput())
    utm_medium = forms.CharField(required=False, widget=forms.HiddenInput())
    utm_campaign = forms.CharField(required=False, widget=forms.HiddenInput())
    utm_term = forms.CharField(required=False, widget=forms.HiddenInput())
    utm_content = forms.CharField(required=False, widget=forms.HiddenInput())
