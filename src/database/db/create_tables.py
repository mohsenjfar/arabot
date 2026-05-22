from . import engine, Base

def create_all():
    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    create_all()
    print('Tables created')
