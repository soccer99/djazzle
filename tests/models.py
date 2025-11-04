from django.db import models

class User(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField(null=True)
    email = models.EmailField()
    username = models.CharField(max_length=100)
    address = models.CharField(max_length=100)

class Pet(models.Model):
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=50)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets')
