from functools import wraps
# decorator to call next on a coroutine
def coroutine(func):
    @wraps(func)
    def dec(*args, **kwargs):
        c = func(*args, **kwargs)
        c.next()
        return c
    return dec

def coroutine_scheduler():
    pass
