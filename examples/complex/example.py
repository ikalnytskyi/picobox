import picobox


@picobox.pass_('conf')
def session(conf):
    class Session:
        connection = conf['connection']
    return Session()


@picobox.pass_('session')
def compute(session):
    print(session.connection)


box = picobox.Box()
box.put('conf', {'connection': 'sqlite://'})
box.put('session', factory=session)

with picobox.push(box):
    compute()
