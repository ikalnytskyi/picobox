import concurrent.futures
import threading

import picobox
import requests


@picobox.pass_('session')
def spam(session):
    return 'thread={}; session={}; ip={}'.format(
        threading.get_ident(),
        id(session),
        session.get('https://httpbin.org/ip').json()['origin'])


# According to https://github.com/kennethreitz/requests/issues/2766
# requests.Session() is not thread-safe. Therefore we need to create
# a separate session for each thread.
box = picobox.Box()
box.put('session', factory=requests.Session, scope=picobox.threadlocal)

with picobox.push(box):
    # We have 3 threads and 10 spam calls which means there should be no more
    # than 3 different session instances (check session ID in the output).
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(spam) for _ in range(10)]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
