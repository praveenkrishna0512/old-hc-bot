class Prize(object):
    # MAKE PRIZE SERIALIZABLE
    def __init__(self, id, name):
        self.id = int(id)
        self.name = name
        self.heldBy = None

    def toJSON(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "heldBy": self.heldBy
        }