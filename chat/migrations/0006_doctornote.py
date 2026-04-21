from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("children", "0002_child_gender_child_notes"),
        ("chat", "0005_message_attachment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DoctorNote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "template_type",
                    models.CharField(
                        choices=[
                            ("initial_assessment", "Initial Assessment"),
                            ("follow_up", "Follow-up"),
                            ("diagnosis", "Diagnosis"),
                        ],
                        default="initial_assessment",
                        max_length=40,
                    ),
                ),
                ("chief_complaint", models.TextField(blank=True)),
                ("clinical_observations", models.TextField(blank=True)),
                ("assessment", models.TextField(blank=True)),
                ("plan", models.TextField(blank=True)),
                ("follow_up_instructions", models.TextField(blank=True)),
                ("is_finalized", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "chat",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="doctor_notes", to="chat.chat"),
                ),
                (
                    "child",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="doctor_notes", to="children.child"),
                ),
                (
                    "doctor",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="doctor_notes", to=settings.AUTH_USER_MODEL),
                ),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.AddConstraint(
            model_name="doctornote",
            constraint=models.UniqueConstraint(fields=("chat", "doctor"), name="unique_doctor_note_per_chat_doctor"),
        ),
    ]
