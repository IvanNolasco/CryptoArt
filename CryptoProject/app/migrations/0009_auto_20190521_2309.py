# Generated by Django 2.2 on 2019-05-22 04:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_auto_20190521_2308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='paintingrequest',
            name='dateDelivery',
            field=models.DateField(),
        ),
    ]