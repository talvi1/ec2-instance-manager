from flask import Flask

manager = Flask(__name__)

from app import index
from app import config