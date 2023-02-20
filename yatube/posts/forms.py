from django import forms
from .models import Post, Comment


# Добавить поле image в форму
class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("text", "group", "image")

    def clean_text(self):
        data = self.cleaned_data['text']
        if not data:
            raise forms.ValidationError('Введите текст')
        return data


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
