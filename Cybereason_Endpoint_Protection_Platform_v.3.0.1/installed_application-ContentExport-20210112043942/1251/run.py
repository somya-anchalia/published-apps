__author__ = 'IBM'

from .app import app
from qpylib import qpylib

qpylib.create_log()
app.run(debug = False, host='0.0.0.0')