from django.db import migrations

ROLES = ['salesman', 'admin_desk', 'production', 'accountant', 'owner']

def create_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    for role in ROLES:
        Group.objects.get_or_create(name=role)

def remove_role_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=ROLES).delete()

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_role_groups, remove_role_groups),
    ]
