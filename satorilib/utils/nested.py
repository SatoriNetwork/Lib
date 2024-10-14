class Nested():

    def __init__(self, up=None, top=None):
        self.up = up or self
        self.top = top or self
