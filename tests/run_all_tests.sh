#!/bin/bash
PYTHONPATH=`pwd`:`pwd`/..:$PYTHONPATH

echo "** Core **"
django-admin.py test core --settings=settings_core

echo
echo
echo "** Basic **"
django-admin.py test basic --settings=settings_basic
