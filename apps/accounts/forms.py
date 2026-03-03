from django import forms
from django.contrib.auth import get_user_model

# Get your active User model (which contains the Role choices and full_name)
User = get_user_model()

class SignupForm(forms.ModelForm):
    # Define password and fullname explicitly since they need special handling
    fullname = forms.CharField(max_length=255, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'role']

    # Custom Email Validation
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with that email address already exists.")
        return email

    # Custom Username Validation (Overrides Django's default message)
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("That username is already taken. Please choose another.")
        return username

    # Custom Save Method
    def save(self, commit=True):
        # Create the user object but don't hit the database yet
        user = super().save(commit=False)
        
        # Securely hash the password.
        user.set_password(self.cleaned_data["password"])
        
        # Assign the custom fullname field
        user.full_name = self.cleaned_data["fullname"]
        
        if commit:
            user.save()
        return user