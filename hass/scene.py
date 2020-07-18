

class SceneActivator:

    def __init__(self, *entities, domain_states, delay=0):
        self.entities = entities
        self.domain_states = domain_states
        self.delay = delay
        self.next_scene = None

    def assign_next(self, next_scene):
        self.next_scene = next_scene

    def run(self):

        """ Sets states on applicable entities """

        all = self.domain_states['all'].items()
        default = self.domain_states['default'].items()

        for entity in self.entities:
            # Apply 'all'
            for attr, value in all:
                # assert hasattr(entity, attr)
                setattr(entity, attr, value)
            if (domain := entity._domain) in self.domain_states:
                for attr, value in self.domain_states[domain].items():
                    # assert hasattr(entity, attr)
                    setattr(entity, attr, value)
            else:
                for attr, value in default:
                    # assert hasattr(entity, attr)
                    setattr(entity, attr, value)


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

    def __call__(self, *entities, delayed=0) -> SceneActivator:
        return SceneActivator(*entities, domain_states=self.domain_states, delay=max(delayed, 0))
