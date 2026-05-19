def test_resource_price_and_total(in_memory_db):
    db, session = in_memory_db
    import database.models_sqlalchemy as models

    # Create resource
    r = models.Resource(title='Sugar', unit='kg')
    session.add(r)
    session.commit()

    # Add prices
    p1 = models.ResourcePrice(resource=r, price=50)
    p2 = models.ResourcePrice(resource=r, price=60)
    session.add_all([p1, p2])
    session.commit()

    # Add logs (completed)
    l1 = models.ResourceLog(resource=r, quantity=2, completed=True)
    l2 = models.ResourceLog(resource=r, quantity=3, completed=True)
    session.add_all([l1, l2])
    session.commit()

    session.refresh(r)
    total = r.total_available()
    assert total == 5


def test_task_message_empty(in_memory_db):
    db, session = in_memory_db
    import database.models_sqlalchemy as models

    parent = models.Parent(title='P')
    session.add(parent)
    session.commit()

    t = models.Task(parent=parent, summary='T1')
    session.add(t)
    session.commit()

    msg = t.message()
    assert isinstance(msg, str)
    assert 'جمع ارزش' in msg
