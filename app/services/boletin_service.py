class BoletinService:
    def __init__(self, boletin_repository):
        self.boletin_repository = boletin_repository

    def get_boletin_by_id(self, boletin_id):
        return self.boletin_repository.get_by_id(boletin_id)

    def create_boletin(self, data):
        return self.boletin_repository.create(data)

    def update_boletin(self, boletin_id, data):
        return self.boletin_repository.update(boletin_id, data)

    def delete_boletin(self, boletin_id):
        return self.boletin_repository.delete(boletin_id)