from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ctrg_app', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE proposals ADD COLUMN revision_deadline DATETIME NULL DEFAULT NULL;",
            reverse_sql="ALTER TABLE proposals DROP COLUMN revision_deadline;",
        ),
    ]
