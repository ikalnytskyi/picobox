import picobox


def spam():
    return eggs()


def eggs():
    return rice()


@picobox.pass_('secret')
def rice(secret):
    print(secret)


with picobox.push(picobox.Box()) as box:
    box.put('secret', 42)

    # We don't need to propagate a secret down to rice which is good because
    # we kept interface clear (i.e. no changes in spam and eggs signatures).
    spam()

    # The other good thing is despite injection rice can explicitly receive
    # a secret which means its signature wasn't changed either.
    rice(13)
