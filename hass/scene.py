

class Scene:

    """ Defines attributes of a scene

        Scenes are designed to be portable:
            e.g. reused across many rooms and entities
            modified all from one place in the code
    """

    def __init__(self, default=None, all=None, **domain_states):
        domain_states = domain_states
        domain_states.update({
            'default': default or {},
            'all': all or {},
        })
        self.domain_states = domain_states

    def __call__(self, *entities, delayed=0, filter=None):
        for entity in entities:
            entity.add_scene(self, delayed, filtered=filter)
