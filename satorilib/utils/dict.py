class MultiKeyDict:

    @staticmethod
    def dict_to_namedtuple(d: dict, tuple_name="DynamicTuple"):
        from collections import namedtuple
        NT = namedtuple(tuple_name, d.keys())
        return NT(**d)

    # Example usage
    # some_dict = {"color": "red", "cost": 4.99, "store_id": 123}
    # nt = dict_to_namedtuple(some_dict)
    # print(nt.color)     # "red"
    # print(nt.cost)      # 4.99
    # print(nt.store_id)  # 123

    @staticmethod
    def deterministic_hash(obj):
        # Use SHA256 for consistent hashing
        import hashlib
        h = hashlib.sha256()
        h.update(repr(obj).encode('utf-8'))
        return int(h.hexdigest(), 16)

    @staticmethod
    def dict_to_tuples(d: dict) -> tuple:
        '''
        guarantee order of keys by generating a unique deterministic hash of
        each and ordering the items by the hash
        '''
        hashFunction = MultiKeyDict.deterministic_hash
        if len(d.keys()) > 1:
            representation = set([
                MultiKeyDict.deterministic_hash(k)
                for k in d.keys()])
            if len(representation) != len(d.keys()):
                # not deterministic across runs, but at least unique per key:
                hashFunction = hash
        sorted_items = sorted(
            d.items(),
            key=lambda item: hashFunction(item[0]))
        return tuple(sorted_items)

    @staticmethod
    def _convert_keys(keys):
        if isinstance(keys, str) or isinstance(keys, int) or isinstance(keys, float):
            return (keys,)
        if isinstance(keys, dict):
            return MultiKeyDict.dict_to_tuples(keys)
        return keys

    def __init__(
        self,
        *args,
        namedTupleName: str = None,
        convertToNamedTuple: bool = True,
        includeKeys: bool = True,
        **kwargs
    ):
        self._store = {}
        self.namedTupleName = namedTupleName or "AutoNamedTuple"
        self.convertToNamedTuple = convertToNamedTuple
        self.includeKeys = includeKeys
        self.args = args
        self.kwargs = kwargs

    def __setitem__(self, keys, value):
        """
        You can pass in a single string or any iterable (e.g. tuple, list).
        Internally, we convert them to a frozenset so the dictionary
        doesn't care about order, and you won't accidentally create
        duplicates by reordering the keys.
        """
        if self.convertToNamedTuple and isinstance(value, dict):
            value = MultiKeyDict.dict_to_namedtuple(
                {**keys, **
                    value} if self.includeKeys and isinstance(keys, dict) else value,
                tuple_name=self.namedTupleName)
        keys = MultiKeyDict._convert_keys(keys)
        self._store[frozenset(keys)] = value

    def __getitem__(self, keys):
        keys = MultiKeyDict._convert_keys(keys)
        return self._store[frozenset(keys)]

    def __contains__(self, keys):
        keys = MultiKeyDict._convert_keys(keys)
        return frozenset(keys) in self._store

    def keys(self):
        return self._store.keys()

    def values(self):
        return self._store.values()

    def items(self):
        return self._store.items()

    def get_values_by_single_key(self, key):
        """
        If you only know one of the keys that might be inside a frozenset
        with other keys, you can scan for it.
        """
        if isinstance(key, dict):
            key = MultiKeyDict.dict_to_tuples(key)[0]
        return [val for kset, val in self._store.items() if key in kset]

    def get(self, keys, default=None):
        keys = MultiKeyDict._convert_keys(keys)
        return self._store.get(frozenset(keys), default)

# Test it out
# mkd = MultiKeyDict(namedTupleName="Fruit")
# mkd[("apple", "banana")] = {"color": "mixed", "cost": 2.99}
# val = mkd["banana", "apple"]
# print(val.color)  # -> "mixed"
# mkd.get(('banana', 'apple'), 'unknown')
# mkd1 = MultiKeyDict(namedTupleName="Fruit")
# mkd1[{'breakfast':'apple', 'lunch': 'banana'}] = {"color": "mixed", "cost": 2.99}
# mkd1.get_values_by_single_key({'lunch': 'banana'})
# mkd1.get({'lunch': 'banana','breakfast':'apple'})
