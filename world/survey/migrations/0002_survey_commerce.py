# Generated for survey data commerce v1.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("survey", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyMarketTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("transaction_type", models.CharField(db_index=True, max_length=32)),
                ("dataset_name", models.CharField(blank=True, default="", max_length=128)),
                ("root_dataset_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("source_dataset_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("seller_scope", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                ("seller_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("seller_name", models.CharField(blank=True, default="", max_length=128)),
                ("buyer_scope", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                ("buyer_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("buyer_name", models.CharField(blank=True, default="", max_length=128)),
                ("price", models.IntegerField(default=0)),
                ("currency", models.CharField(default="credits", max_length=32)),
                ("status", models.CharField(db_index=True, default="complete", max_length=32)),
                ("exchange_key", models.CharField(blank=True, db_index=True, default="", max_length=128)),
                ("exchange_name", models.CharField(blank=True, default="", max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="market_transactions",
                        to="survey.surveydataset",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["transaction_type", "created_at"], name="survey_sur_transac_a06f01_idx"),
                    models.Index(fields=["seller_scope", "seller_id"], name="survey_sur_seller__501bfb_idx"),
                    models.Index(fields=["buyer_scope", "buyer_id"], name="survey_sur_buyer_s_4502ce_idx"),
                    models.Index(fields=["dataset"], name="survey_sur_dataset_f9032a_idx"),
                    models.Index(fields=["root_dataset_id"], name="survey_sur_root_da_e4e2ea_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SurveyTradeOffer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dataset_name", models.CharField(blank=True, default="", max_length=128)),
                ("seller_scope", models.CharField(db_index=True, max_length=32)),
                ("seller_id", models.IntegerField(db_index=True)),
                ("seller_name", models.CharField(blank=True, default="", max_length=128)),
                ("buyer_scope", models.CharField(db_index=True, max_length=32)),
                ("buyer_id", models.IntegerField(db_index=True)),
                ("buyer_name", models.CharField(blank=True, default="", max_length=128)),
                ("mode", models.CharField(db_index=True, default="transfer", max_length=32)),
                ("price", models.IntegerField(default=0)),
                ("currency", models.CharField(default="credits", max_length=32)),
                ("requested_is_transferable", models.BooleanField(default=True)),
                ("requested_is_copyable", models.BooleanField(default=True)),
                ("requested_license_mode", models.CharField(default="transferable", max_length=64)),
                ("status", models.CharField(db_index=True, default="pending", max_length=32)),
                ("seller_location_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("buyer_location_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="trade_offers",
                        to="survey.surveydataset",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["seller_scope", "seller_id", "status"], name="survey_sur_seller__6fca91_idx"),
                    models.Index(fields=["buyer_scope", "buyer_id", "status"], name="survey_sur_buyer_s_582ec2_idx"),
                    models.Index(fields=["status", "expires_at"], name="survey_sur_status_59b145_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="SurveyCopyEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("root_dataset_id", models.IntegerField(db_index=True)),
                ("event_type", models.CharField(db_index=True, max_length=32)),
                ("actor_scope", models.CharField(blank=True, db_index=True, default="", max_length=32)),
                ("actor_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("object_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="copy_events",
                        to="survey.surveydataset",
                    ),
                ),
                (
                    "source_dataset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="copy_events_as_source",
                        to="survey.surveydataset",
                    ),
                ),
                (
                    "transaction",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="copy_events",
                        to="survey.surveymarkettransaction",
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["root_dataset_id", "event_type"], name="survey_sur_root_da_2dd9dc_idx"),
                    models.Index(fields=["actor_scope", "actor_id"], name="survey_sur_actor__f73f7b_idx"),
                    models.Index(fields=["created_at"], name="survey_sur_created_3aa406_idx"),
                ],
            },
        ),
    ]
