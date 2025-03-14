import sys

if "client_local" in sys.argv[0]:
    from .database_local import db
elif any("server_remote" in arg for arg in sys.argv):
    from .database_remote import db
else:
    from .database_local import db