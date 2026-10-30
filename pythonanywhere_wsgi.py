# -*- coding: utf-8 -*-
"""
PythonAnywhere WSGI entry file — Phosphate Grinding Mill System.

HOW TO USE (full steps in DEPLOY-STEPS.txt):
  1. In the Web tab, open the link "WSGI configuration file"
     (it looks like /var/www/YOURUSERNAME_pythonanywhere_com_wsgi.py).
  2. Delete everything in that file.
  3. Paste THIS file's contents instead, after replacing YOURUSERNAME
     below with the PythonAnywhere username, and save.
  4. Press the green Reload button on the Web tab.
"""

import os
import sys

# Folder where app.py + wsgi_adapter.py were uploaded
# (the account's home folder is /home/YOURUSERNAME).
PROJECT_HOME = "/home/YOURUSERNAME/mill"
if PROJECT_HOME not in sys.path:
    sys.path.insert(0, PROJECT_HOME)

# The mill system itself. app.py's main() is never called under WSGI, so
# the PC-only biometric LAN listener stays off — see DEPLOY-STEPS.txt.
from wsgi_adapter import application  # noqa: F401,E402
