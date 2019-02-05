class Reporter:
    @staticmethod
    def reporter(self):
        pass


class Dict(dict, Reporter):
    def update(self, *args, **kwds):
        dict.update(self, *args, **kwds)
        self.reporter()

    def __setitem__(self, k, v):
        dict.__setitem__(self, k, v)
        self.reporter()


class List(dict, Reporter):
    def update(self, *args, **kwds):
        list.update(self, *args, **kwds)
        self.reporter()

    def __setitem__(self, k, v):
        list.__setitem__(self, k, v)
        self.reporter()


def add_reporter(x, reporter):
    if isinstance(x, dict):
        return {k: add_reporter(v, reporter) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        pass
