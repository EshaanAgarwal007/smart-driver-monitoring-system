from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import DriverProfile


class DriverRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': 'Choose a username'
    }))
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': 'your@email.com'
    }))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': '••••••••'
    }))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': '••••••••'
    }))

    class Meta:
        model = DriverProfile
        fields = [
            'full_name', 'age', 'date_of_birth', 'mobile',
            'address', 'vehicle_number', 'license_number',
            'vehicle_brand', 'vehicle_model',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control avalon-input', 'placeholder': 'Full Name'}),
            'age': forms.NumberInput(attrs={'class': 'form-control avalon-input', 'placeholder': 'Age', 'min': 18, 'max': 80}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control avalon-input', 'type': 'date'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control avalon-input', 'placeholder': '+91 XXXXX XXXXX'}),
            'address': forms.Textarea(attrs={'class': 'form-control avalon-input', 'placeholder': 'Full address', 'rows': 3}),
            'vehicle_number': forms.TextInput(attrs={'class': 'form-control avalon-input', 'placeholder': 'MH 01 AB 1234'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control avalon-input', 'placeholder': 'DL-XXXXXXXXXXXXXXXX'}),
            'vehicle_brand': forms.Select(attrs={'class': 'form-select avalon-input'}),
            'vehicle_model': forms.TextInput(attrs={'class': 'form-control avalon-input', 'placeholder': 'e.g. Camry, Swift, i20'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
        )
        profile.user = user
        if commit:
            profile.save()
        return profile


class DriverLoginForm(forms.Form):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': 'Username'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control avalon-input', 'placeholder': '••••••••'
    }))
