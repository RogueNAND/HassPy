import asyncio, time
from .push import push


class Schedule:
    def __init__(self, loop):
        self.scheduled_functions = []
        loop.create_task(self.task_loop())

    def schedule_function(self, func, t, *args, **kwargs):
        self.scheduled_functions.append((t, func, args, kwargs))

    async def task_loop(self):
        while True:
            # TODO: Popping indexes seems jank. Pls improve thx.
            current_time = time.time()

            # Get functions that have passed the scheduled run time
            # List is sorted and reversed so the most recent one is first
            items_to_pop = [
                i
                for i, f in enumerate(self.scheduled_functions)
                if current_time >= f[0]
            ]  # Get indexes
            funcs_to_run = [self.scheduled_functions[i] for i in items_to_pop]
            funcs_to_run = sorted(funcs_to_run, key=lambda x: x[0], reverse=True)

            if funcs_to_run:
                self._run_functions(funcs_to_run)

                # Pop indexes
                for i in sorted(items_to_pop, reverse=True):
                    del self.scheduled_functions[i]

            await asyncio.sleep(1)

    @push
    def _run_functions(self, funcs):
        for t, func, args, kwargs in funcs:
            print("Running delayed function:", func)
            func(*args, **kwargs)


loop = asyncio.get_event_loop()
scheduler = Schedule(loop)
