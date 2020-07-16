import asyncio, time


class Schedule:
    def __init__(self, loop):
        self.scheduled_functions = {}
        loop.create_task(self.task_loop())

    def delay_function(self, func, seconds, *args, **kwargs):
        self.scheduled_functions[func] = (time.time() + seconds, args, kwargs)
        print("Scheduler:", func)

    def cancel_function(self, func):
        if func in self.scheduled_functions:
            del self.scheduled_functions[func]
            print("Scheduler canceled:", func)

    async def task_loop(self):
        while True:
            current_time = time.time()
            functions_to_run = []
            for func, values in self.scheduled_functions.items():
                t, args, kwargs = values
                if current_time > t:
                    functions_to_run.append((func, args, kwargs))

            for func, args, kwargs in functions_to_run:
                print("Running delayed function:", func)
                func(*args, **kwargs)
                del self.scheduled_functions[func]
            await asyncio.sleep(1)
