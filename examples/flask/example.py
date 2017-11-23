import picobox
from flask import Flask, jsonify
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
