# Generated by Django 2.0.2 on 2020-08-28 14:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('filtro', '0012_merge_20200826_1858'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='usuarioacessofiltro',
            unique_together={('filtro', 'usuario')},
        ),
    ]