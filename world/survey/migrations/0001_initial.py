# Generated manually from world.survey.models.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SurveyCoverage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("owner_scope", models.CharField(db_index=True, max_length=32)),
                ("owner_id", models.IntegerField(db_index=True)),
                ("system_name", models.CharField(db_index=True, max_length=128)),
                ("body_id", models.CharField(db_index=True, max_length=128)),
                ("body_name", models.CharField(blank=True, default="", max_length=128)),
                ("x", models.IntegerField(db_index=True)),
                ("y", models.IntegerField(db_index=True)),
                ("scan_type", models.CharField(db_index=True, default="terrain", max_length=64)),
                ("resolution", models.IntegerField(db_index=True, default=1)),
                ("quality", models.IntegerField(default=100)),
                ("source_ship_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("source_object_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("first_scanned_at", models.DateTimeField(auto_now_add=True)),
                ("last_scanned_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SurveyDataset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True, default="")),
                ("owner_scope", models.CharField(db_index=True, max_length=32)),
                ("owner_id", models.IntegerField(db_index=True)),
                ("creator_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("source_ship_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("system_name", models.CharField(db_index=True, max_length=128)),
                ("body_id", models.CharField(db_index=True, max_length=128)),
                ("body_name", models.CharField(blank=True, default="", max_length=128)),
                ("scan_type", models.CharField(db_index=True, default="terrain", max_length=64)),
                ("min_resolution", models.IntegerField(default=1)),
                ("max_resolution", models.IntegerField(default=1)),
                ("tile_count", models.IntegerField(default=0)),
                ("integrity", models.IntegerField(default=100)),
                ("is_transferable", models.BooleanField(default=True)),
                ("is_copyable", models.BooleanField(default=True)),
                ("license_mode", models.CharField(default="transferable", max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="SurveyDatasetTile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("system_name", models.CharField(db_index=True, max_length=128)),
                ("body_id", models.CharField(db_index=True, max_length=128)),
                ("body_name", models.CharField(blank=True, default="", max_length=128)),
                ("x", models.IntegerField(db_index=True)),
                ("y", models.IntegerField(db_index=True)),
                ("scan_type", models.CharField(db_index=True, default="terrain", max_length=64)),
                ("resolution", models.IntegerField(default=1)),
                ("quality", models.IntegerField(default=100)),
                ("data", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="tiles",
                        to="survey.surveydataset",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="surveycoverage",
            index=models.Index(fields=["owner_scope", "owner_id"], name="survey_cov_owner_idx"),
        ),
        migrations.AddIndex(
            model_name="surveycoverage",
            index=models.Index(fields=["system_name", "body_id", "x", "y"], name="survey_cov_body_xy_idx"),
        ),
        migrations.AddIndex(
            model_name="surveycoverage",
            index=models.Index(fields=["system_name", "body_id", "scan_type"], name="survey_cov_body_scan_idx"),
        ),
        migrations.AddIndex(
            model_name="surveycoverage",
            index=models.Index(fields=["source_ship_id"], name="survey_cov_ship_idx"),
        ),
        migrations.AddConstraint(
            model_name="surveycoverage",
            constraint=models.UniqueConstraint(
                fields=["owner_scope", "owner_id", "system_name", "body_id", "x", "y", "scan_type"],
                name="unique_survey_coverage_tile",
            ),
        ),
        migrations.AddIndex(
            model_name="surveydataset",
            index=models.Index(fields=["owner_scope", "owner_id"], name="survey_data_owner_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydataset",
            index=models.Index(fields=["creator_id"], name="survey_data_creator_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydataset",
            index=models.Index(fields=["source_ship_id"], name="survey_data_ship_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydataset",
            index=models.Index(fields=["system_name", "body_id"], name="survey_data_body_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydataset",
            index=models.Index(fields=["scan_type"], name="survey_data_scan_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydatasettile",
            index=models.Index(fields=["dataset"], name="survey_tile_dataset_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydatasettile",
            index=models.Index(fields=["system_name", "body_id", "x", "y"], name="survey_tile_body_xy_idx"),
        ),
        migrations.AddIndex(
            model_name="surveydatasettile",
            index=models.Index(fields=["scan_type"], name="survey_tile_scan_idx"),
        ),
        migrations.AddConstraint(
            model_name="surveydatasettile",
            constraint=models.UniqueConstraint(
                fields=["dataset", "system_name", "body_id", "x", "y", "scan_type"],
                name="unique_survey_dataset_tile",
            ),
        ),
    ]
