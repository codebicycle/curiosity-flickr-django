from django import forms


class PeopleForm(forms.Form):
    user_id_or_url = forms.CharField(max_length=255)
    per_page = forms.IntegerField(min_value=1, required=False)
    page = forms.IntegerField(min_value=1, required=False)


class FlickrForm(forms.Form):
    def __init__(self, *args, **kwargs):
        extra = kwargs.pop('extra')
        super().__init__(*args, **kwargs)

        arguments = extra['arguments']['argument']
        for argument in arguments:
            name = argument['name']
            self.fields[name] = forms.CharField()
            self.fields[name].help_text = argument['_content']
            self.fields[name].required = not argument['optional']

        try:
            self.fields['api_key'].required = False
        except KeyError:
            pass

    def clean(self):
        """Remove keys with corresponding empty values '' from cleaned_data
        Fixes bug: if argument max_fave_date is '', no errors are thrown but the results are empty.
        """
        cleaned_data = super().clean()
        clone = cleaned_data.copy()
        for key, value in clone.items():
            if value == '':
                del cleaned_data[key]
        return cleaned_data
