from dataclasses import dataclass, replace

@dataclass(frozen=True)
class CopiableDataclass:
    @classmethod
    def fromInstance(
        cls,
        existing:  "CopiableDataclass",
        **overrides
    ) ->  "CopiableDataclass":
        """
        Create a new instance from an existing instance, optionally
        overriding any fields via keyword arguments.
        Usage:
            new_policy = CopiableDataclass.fromInstance(
                old_policy,
                localAuthentication=True
            )
        """
        return replace(existing, **overrides)
    def copy(self, **overrides) -> "CopiableDataclass":
        """
        Create a new instance from the current instance, optionally
        overriding any fields via keyword arguments.
        Usage:
            new_policy = old_policy.modify(
                localAuthentication=True
            )
        """
        return self.fromInstance(self, **overrides)
