import picobox
from flask import Flask, jsonify, request
from tools import spam


app = Flask('example')


@app.route('/')
def index():
    return jsonify({'spam': spam()})


# @app.route() internally saves wrapped function inside, so decorators order
# here does matter and if you want to inject some argument using picobox,
# you ought to apply @picobox.pass_ before @app.route.
@app.route('/magic')
@picobox.pass_('magic')
def magic(magic):
    return jsonify({'magic': magic})


@app.before_request
def serve_eggs_with_spam():
    box = picobox.Box()

    # on requests to /eggs, override the value of magic with 'spam'
    if request.path == '/eggs':
        box.put('magic', 'spam')

    picobox.push(box, chain=True)


@app.after_request
def take_spam_away(response):
    # pop the box from the top of the stack to remove the override
    picobox.pop()
    return response


@app.route('/eggs')
@picobox.pass_('magic')
def eggs(magic):
    return jsonify({'magic': magic})
