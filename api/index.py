from vercel_wsgi import make_handler
from app import app

handler = make_handler(app)