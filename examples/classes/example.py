import picobox


class Sender:
    def send(self, text):
        print(text)


class Controller:

    # Picobox supports injections by type (key may be any hashable object),
    # though in this case you have to explicitly map the key onto argument
    # name.
    @picobox.pass_(Sender, as_='sender')
    def __init__(self, sender):
        self._sender = sender

    # Many alternative solutions support injections to __init__ only while
    # Picobox allows to inject arguments wherever you want. You are the
    # only one to decide what would be the better way.
    @picobox.pass_('document')
    def process(self, document):
        self._sender.send('processing ' + document)


box = picobox.Box()
box.put(Sender, factory=Sender, scope=picobox.singleton)
box.put('document', 'cv.txt')

with picobox.push(box):
    controller = Controller()
    controller.process()
