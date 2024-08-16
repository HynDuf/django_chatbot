from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Talk(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Untitled Talk")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} ({self.user.username})'

class Chat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    talk = models.ForeignKey(Talk, related_name='chats', on_delete=models.CASCADE)
    message = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username}: {self.message}'
