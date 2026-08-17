import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('jobsearch', '0002_criteriaprofile_include_sponsorship_keyword_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('profile_name', models.CharField(max_length=100)),
                ('new_jobs', models.PositiveIntegerField(default=0)),
                ('skipped_below_threshold', models.PositiveIntegerField(default=0)),
                ('skipped_duplicate', models.PositiveIntegerField(default=0)),
                ('warnings', models.TextField(blank=True, help_text='One per line - which source(s) had trouble and why, if any.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='search_runs', to=settings.AUTH_USER_MODEL)),
                ('profile', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='search_runs', to='jobsearch.criteriaprofile')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
