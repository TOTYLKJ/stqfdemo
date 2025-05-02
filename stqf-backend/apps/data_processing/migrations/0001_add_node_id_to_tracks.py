from django.db import migrations

class Migration(migrations.Migration):
    initial = True

    dependencies = [
    ]

    operations = [
        migrations.RunSQL(
            """
            ALTER TABLE tracks_table
            ADD COLUMN IF NOT EXISTS node_id VARCHAR(20) DEFAULT NULL;
            """,
            """
            ALTER TABLE tracks_table
            DROP COLUMN IF EXISTS node_id;
            """
        ),
    ] 