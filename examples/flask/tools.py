import picobox


def spam():
    return eggs()


def eggs():
    return rice()


@picobox.pass_('magic')
def rice(magic):
    return magic + 1
