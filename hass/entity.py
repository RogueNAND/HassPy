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
            func(*args, **kwargs)
            for entity in push_threads[thread_id]:
                entity.push_changes_to_ha()
            del push_threads[thread_id]
    return inner


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
            func(self, data)

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
        return None

    def __setattr__(self, key, value):

        """ This method is so we can save all changes to a dict before pushing to HA.
            Hopefully to save a few calls...
        """

        thread_id = threading.get_ident()
        if thread_id in push_threads:
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
        entity_type = type(entities[0])
        for e in entities:
            assert isinstance(e, entity_type)
        self.event_calls = set()

        object.__setattr__(self, '__initialized', True)

    @property
    def state(self):
        return any([entity.state for entity in self.entities])

    def add_event_call(self, func):
        for entity in self.entities:
            entity.add_event_call(func)

    def _call_method(self, entities, name):
        for entity in entities:
            getattr(entity, name)()

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
                    return lambda: self._call_method(entities, item)

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
            entities = [e for e in self.entities if hasattr(e, key)]
            for e in entities:
                setattr(e, key, value)
        else:
            object.__setattr__(self, key, value)


entity_classes = {
    e._domain: e
    for e in Entity.__subclasses__()
}
