import uuid


class AnyMixin:
    def __eq__(self, a, *args, **kwargs):
        return isinstance(self, type(a))


class AnyUUID(AnyMixin, uuid.UUID):
    def __eq__(self, a, *args, **kwargs):
        if isinstance(a, str):
            try:
                return self == uuid.UUID(a)
            except Exception:
                return False
        return isinstance(self, type(a))


any_uuid = AnyUUID(uuid.uuid4().hex)
