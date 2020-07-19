from functools import wraps
import threading

push_threads = {}


def push(func):

    @wraps(func)
    def inner(*args, **kwargs):
        thread_id = threading.get_ident()
        if thread_id in push_threads:
            func(*args, **kwargs)
        else:
            push_threads[thread_id] = set()
            result = func(*args, **kwargs)
            for entity in push_threads[thread_id]:
                entity.push_changes_to_ha()
            del push_threads[thread_id]
            return result
    return inner
