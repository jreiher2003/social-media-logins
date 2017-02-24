from app import app, db 
from flask_script import Manager,Server

server = Server(host="0.0.0.0",port=9998)
manager = Manager(app)
manager.add_command("runserver",server)

@manager.command 
def dropdb():
    print "drop all tables"
    db.drop_all()

@manager.command 
def createall():
    print "just created all tables"
    db.create_all()

if __name__ == "__main__":
    manager.run()
