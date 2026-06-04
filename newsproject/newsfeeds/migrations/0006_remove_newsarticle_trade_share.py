# Generated migration to remove trade_share field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('newsfeeds', '0005_newsarticle_origin'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='newsarticle',
            name='trade_share',
        ),
    ]
