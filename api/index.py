from vercel import wsgi
from app import app

wsgi.app = app