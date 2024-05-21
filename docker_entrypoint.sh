python manage.py migrate
python manage.py create_user --username user --password password --is_admin
python manage.py create_consumer_pair --consumer consumer --secret secret --expire_in_weeks 520 --no-update
python manage.py runserver 0.0.0.0:8000


