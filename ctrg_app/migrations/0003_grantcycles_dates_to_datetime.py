from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ctrg_app', '0002_proposals_revision_deadline'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE grantcycles
                    MODIFY COLUMN stage1_start_date DATETIME NULL DEFAULT NULL,
                    MODIFY COLUMN stage1_end_date   DATETIME NULL DEFAULT NULL,
                    MODIFY COLUMN stage2_start_date DATETIME NULL DEFAULT NULL,
                    MODIFY COLUMN stage2_end_date   DATETIME NULL DEFAULT NULL;
            """,
            reverse_sql="""
                ALTER TABLE grantcycles
                    MODIFY COLUMN stage1_start_date DATE NULL DEFAULT NULL,
                    MODIFY COLUMN stage1_end_date   DATE NULL DEFAULT NULL,
                    MODIFY COLUMN stage2_start_date DATE NULL DEFAULT NULL,
                    MODIFY COLUMN stage2_end_date   DATE NULL DEFAULT NULL;
            """,
        ),
    ]
