from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ctrg_app', '0003_grantcycles_dates_to_datetime'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                UPDATE grantcycles SET revision_duration_days = NULL;
                ALTER TABLE grantcycles MODIFY COLUMN revision_duration_days DATETIME NULL DEFAULT NULL;
            """,
            reverse_sql="ALTER TABLE grantcycles MODIFY COLUMN revision_duration_days INT NULL DEFAULT NULL;",
        ),
    ]
