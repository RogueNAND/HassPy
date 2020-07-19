import threading, time, math
from .hass import scheduler
from .push import push, push_threads


class Entity:
    _domain = ''

    def __init__(self, ha, id):
        # if not self._domain:
        #     raise NotImplementedError(f"{self.__class__.__name__}: '_domain' not set")
        self.ha = ha
        ha.add_entity_listener(id, self)
        self.id = id
        self.event_calls = set()
        self.state = None
        self.scenes = {}
        self._modified_values = {}

    def toggle(self):
        if self.state is True:
            self.state = False
        elif self.state is False:
            self.state = True

    def add_event_call(self, func):
        self.event_calls.add(func)

    def call(self, msg):
        if 'new_state' in msg['data']:
            data = msg['data']['new_state']
        else:
            data = msg['data']

        self._set_attributes_from_json(data)

        # Call watched functions
        self._call_watched_methods(data)

    @push
    def _call_watched_methods(self, data):
        for func in self.event_calls:
            scene_activator = func(self, data)

            if scene_activator:
                # Run all, if multiple
                if isinstance(scene_activator, tuple):
                    for activator in scene_activator:
                        activator.run()
                else:
                    scene_activator.run()

    def _set_attributes_from_json(self, data, state=None):
        if 'new_state' in data:
            data = data['new_state']
        else:
            data = data

        # Set attributes
        for attr, value in data.items():
            setattr(self, attr, value)

        if state is not None:
            self.state = state

        if self.state in ['on']:
            self.state = True
        elif self.state in ['off']:
            self.state = False

    def push_changes_to_ha(self):
        if 'state' in self._modified_values:
            del self._modified_values['state']
        self.ha.call_service(self, {k: v for k, v in self._modified_values.items()})
        object.__setattr__(self, '_modified_values', {})

    def compute_service(self):
        """ Override this method """
        return None

    """ Scene control """

    def add_scene(self, scene, delay=0):
        if delay > 1:
            time_to_run = time.time() + delay

            # Remove all scenes that were currently scheduled after this new scene
            for t in filter(lambda x: x[0] + 1 >= time_to_run, self.scenes.values()):
                del self.scenes[t]

            # Schedule the new scene
            self.scenes[time_to_run] = scene
            scheduler.schedule_function(self.run_scene_schedule, time_to_run)

        else:
            self._call_scene(scene)
            object.__setattr__(self, 'scenes', {})

    def run_scene_schedule(self):
        current_time = math.ceil(time.time())

        # Get scenes that have passed the scheduled run time
        # List is sorted and reversed so the most recent one is first
        scenes_to_run = sorted([
            (t, scene)
            for t, scene in self.scenes.items()
            if current_time >= t
        ], reverse=True)

        # Run and delete scenes
        for t, scene in scenes_to_run:
            self._call_scene(scene)
            del self.scenes[t]

    def _call_scene(self, scene):

        """ Immediately apply a scene to this entity """

        # Get attributes from scene
        all_attrs = scene.domain_states.get('all', {})
        if self._domain in scene.domain_states:
            self_attrs = scene.domain_states.get(self._domain, {})
        else:
            self_attrs = scene.domain_states.get('default', {})

        # Apply attributes
        for attr, value in all_attrs.items():
            setattr(self, attr, value)
        for attr, value in self_attrs.items():
            setattr(self, attr, value)

    def __setattr__(self, key, value):

        """ This method is so we can save all changes to a dict before pushing to HA.
            Hopefully to save a few calls...
        """

        thread_id = threading.get_ident()
        if thread_id in push_threads:
            # Only update HomeAssistant if a change has been made
            if not hasattr(self, key) or getattr(self, key) != value:
                object.__setattr__(self, key, value)
                self._modified_values[key] = value
                push_threads[thread_id].add(self)
        else:
            object.__setattr__(self, key, value)

    def __str__(self):
        return f"<Entity: {self.id}>"


class Light(Entity):
    _domain = 'light'

    def compute_service(self):
        if self.state:
            return 'turn_on'
        else:
            return 'turn_off'


class BinarySensor(Entity):
    _domain = 'binary_sensor'


class MediaPlayer(Entity):
    _domain = 'media_player'


class Sensor(Entity):
    _domain = 'sensor'


class Switch(Entity):
    _domain = 'switch'


class Group:
    def __init__(self, *entities):
        object.__setattr__(self, '__initialized', False)

        self.entities = entities
        entity_domain = entities[0]._domain
        for e in entities:
            assert e._domain == entity_domain
        self.event_calls = set()

        object.__setattr__(self, '__initialized', True)

    @property
    def state(self):
        return any([entity.state for entity in self.entities])

    def add_event_call(self, func):
        for entity in self.entities:
            entity.add_event_call(func)

    def _call_method(self, entities, name, *args, **kwargs):
        for entity in entities:
            getattr(entity, name)(*args, **kwargs)

    def __iter__(self):
        return self.entities.__iter__()

    def __getattr__(self, item):

        """ Culminate children values into a single value """

        # Get applicable entities
        entities = [
            e for e in self.entities
            if hasattr(e, item)
        ]

        if entities:
            # If method
            for e in entities:
                if callable(getattr(e, item)):
                    return lambda *args, **kw: self._call_method(entities, item, *args, *kw)

            all_values = [
                getattr(e, item)
                for e in entities
            ]

            # Remove Falsy values except 0
            values = [
                v for v in all_values
                if v or v == 0
            ]

            # Check if all values are equal
            if len(set(values)) == 1:
                return values[0]

            # Otherwise, take average value
            value = sum([
                getattr(entity, item)
                for entity in entities
            ]) / len(entities)
            return value
        else:
            return None

    def __setattr__(self, key, value):

        """ Pass off attribute values to children """

        if self.__getattribute__('__initialized'):
            entities = [e for e in self.entities]
            for e in entities:
                setattr(e, key, value)
        else:
            object.__setattr__(self, key, value)


entity_classes = {
    e._domain: e
    for e in Entity.__subclasses__()
}
