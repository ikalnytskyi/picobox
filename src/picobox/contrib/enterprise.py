"""Enterprise grade synonyms."""

import picobox

Container = picobox.Box
Container.inject = Container.pass_

MultiContainer = picobox.ChainBox

get = picobox.get
put = picobox.put
inject = picobox.pass_

_ = picobox.push
_ = picobox.pop
_ = picobox.Stack
_ = picobox.Scope

_ = picobox.noscope
_ = picobox.singleton
_ = picobox.threadlocal
_ = picobox.contextvars
