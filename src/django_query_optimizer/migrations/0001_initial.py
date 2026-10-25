from typing import ClassVar

from django.db import migrations
from django.db.migrations.operations.base import Operation


class Migration(migrations.Migration):
    """Initial migration — declares the unmanaged QueryLog proxy model.

    ``QueryLog`` has ``managed = False`` so no table is created.
    This migration exists solely so that Django can register the
    ``ContentType`` and ``Permission`` rows needed by the admin.
    """

    initial = True
    dependencies: ClassVar[list[tuple[str, str]]] = []

    operations: ClassVar[list[Operation]] = [
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
