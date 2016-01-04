from collections import MutableMapping


class HttpHeaders(MutableMapping):
    def __init__(self, **kwargs):
        self._dict = {self.normalize_key(k): [v] for k, v in kwargs.iteritems()}

    def __setitem__(self, key, value):
        self._dict.setdefault(self.normalize_key(key), []).append(value)

    def __getitem__(self, key):
        return self._dict[self.normalize_key(key)][-1]

    def __contains__(self, key):
        return self.normalize_key(key) in self._dict.keys()

    def __delitem__(self, key):
        del self._dict[self.normalize_key(key)]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def append(self, key, value):
        self._dict.setdefault(self.normalize_key(key), []).append(value)

    def get_list(self, key):
        return self._dict.get(self.normalize_key(key), [])

    def as_list(self):
        return [(k, self.get(k)) for k in self._dict.keys()]

    @staticmethod
    def normalize_key(key):
        return '-'.join(w.capitalize() for w in key.split('-'))
