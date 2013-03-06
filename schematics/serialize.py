# encoding=utf-8

from .types.compound import ModelType, ListType
from .models import Model


def serializable(*args, **kwargs):
    def wrapper(f):
        return SerializableType(f, serialized_name=kwargs.get("serialized_name", None))

    if len(args) == 1 and callable(args[0]):
        # No arguments, this is the decorator
        # Set default values for the arguments
        return wrapper(args[0])
    else:
        return wrapper


class SerializableType(property):

    # def __init__(self, f, serialized_name=None):
    #     self.f = f
    #     self.serialized_name = serialized_name

    # def __call__(self, serialized_name=None):
    #     self.serialized_name = serialized_name
    #     return self

    def __init__(self, *args, **kwargs):
        print args, kwargs
        self.serialized_name = kwargs.pop("serialized_name", None)

        super(SerializableType, self).__init__(*args, **kwargs)

    def to_primitive(self, value):
        return value


def _reduce_loop(model):
    """Each field's name, the field MODEL and the field's value are
    collected in a truple and yielded, making this a generator.
    """
    model_class = model.__class__
    for field_name in model:
        if field_name not in model:
            continue
        field_instance = model_class._fields[field_name]
        field_value = model[field_name]
        yield (field_name, field_instance, field_value)

    print model_class.__dict__
    is_serializable = lambda k_v: isinstance(k_v[1], SerializableType)
    for field_name, serializable_instance in filter(is_serializable, model_class.__dict__.iteritems()):
        print field_name, serializable_instance, getattr(model, field_name)
        yield field_name, serializable_instance, getattr(model, field_name)


def apply_shape(model, model_converter, role, gottago):
    model_dict = {}

    # Loop over each field and either evict it or convert it
    for (field_name, field_instance, field_value) in _reduce_loop(model):

        # Check for alternate field name
        serialized_name = field_name
        if field_instance.serialized_name:
            serialized_name = field_instance.serialized_name

        # Evict field if it's gotta go
        if gottago(field_name, field_value):
            continue

        if field_value is None:
            model_dict[serialized_name] = None
            continue

        # Convert field as single model
        if isinstance(field_instance, ModelType):
            model_dict[serialized_name] = model_converter(field_value)
            continue

        # Convert field as list of models
        if isinstance(field_instance, ListType):
            if field_value and isinstance(field_value[0], Model):
                model_dict[serialized_name] = [model_converter(vi)
                                               for vi in field_value]
                continue

        # Convert field as single field
        model_dict[serialized_name] = field_instance.to_primitive(field_value)

    return model_dict


#
# Field Access Functions
#

def wholelist(*field_list):
    """Returns a function that evicts nothing. Exists mainly to be an explicit
    allowance of all fields instead of a using an empty blacklist.
    """
    def _wholelist(k, v):
        return False
    return _wholelist


def whitelist(*field_list):
    """Returns a function that operates as a whitelist for the provided list of
    fields.

    A whitelist is a list of fields explicitly named that are allowed.
    """
    # Default to rejecting the value
    _whitelist = lambda k, v: True

    if field_list is not None and len(field_list) > 0:
        def _whitelist(k, v):
            return k not in field_list

    return _whitelist


def blacklist(*field_list):
    """Returns a function that operates as a blacklist for the provided list of
    fields.

    A blacklist is a list of fields explicitly named that are not allowed.
    """
    # Default to not rejecting the value
    _blacklist = lambda k, v: False

    if field_list is not None and len(field_list) > 0:
        def _blacklist(k, v):
            return k in field_list

    return _blacklist


def serialize(instance, role, **kw):
    model = instance.__class__
    model_converter = lambda m: serialize(m, role)

    gottago = lambda k, v: False
    if role in model._options.roles:
        gottago = model._options.roles[role]
    elif role:
        raise ValueError(u'%s Model has no role "%s"' % (
            instance.__class__.__name__, role))

    return apply_shape(instance, model_converter, role, gottago, **kw)
