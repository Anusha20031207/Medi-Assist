# Generated manually for RAG DocumentChunk

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_feedbackmodel_feedback_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentChunk',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(help_text='e.g. filename or document title', max_length=500)),
                ('text', models.TextField(help_text='Chunk text content')),
                ('embedding_json', models.TextField(blank=True, help_text='JSON array of embedding floats', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'RAG_DocumentChunks',
                'ordering': ['source', 'id'],
            },
        ),
    ]
