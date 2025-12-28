from vercel_wsgi import handler
from app import app

app = handler(app)