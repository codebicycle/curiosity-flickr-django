from django import forms


class PeopleForm(forms.Form):
    user_id_or_url = forms.CharField(max_length=255)
    per_page = forms.IntegerField(min_value=1, required=False)
    page = forms.IntegerField(min_value=1, required=False)
