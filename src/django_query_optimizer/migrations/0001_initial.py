from django.db import migrations


class Migration(migrations.Migration):
    """Initial migration — declares the unmanaged QueryLog proxy model.

    ``QueryLog`` has ``managed = False`` so no table is created.
    This migration exists solely so that Django can register the
    ``ContentType`` and ``Permission`` rows needed by the admin.
    """

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="QueryLog",
            fields=[],
            options={
                "managed": False,
                "verbose_name": "Query Optimizer",
                "verbose_name_plural": "Query Optimizer",
            },
        ),
    ]
