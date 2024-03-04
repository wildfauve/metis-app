from dataclasses import dataclass

from metis_fn import monad, fn
from metis_app import error


class DynamoDB():
    def __init__(self):
        self.table = {}

    def save(self, model):
        self.table[model.hash_key] = {model.range_key: model}
        return model

    def get(self, pk, sk):
        result = fn.deep_get(self.table, [pk, sk])
        if result:
            return result
        raise error.BaseError("Item Not Found")


@dataclass
class Circuit:
    hash_key: str
    range_key: str
    failures: int
    circuit_state: str | None
    last_state_chg_time: str | None

    def save(self):
        DB.save(self)


DB = DynamoDB()


class DynamoError(error.BaseError):
    def not_found(cls):
        return "DoesNotExist" in cls.klass


def find_or_create_circuit(domain) -> Circuit:
    circuit = find_circuit_by_id(domain.circuit_name)
    if circuit.is_left():
        return create_circuit(domain.circuit_name)
    return circuit.value


def create_circuit(circuit_name) -> Circuit:
    repo = Circuit(hash_key=format_circuit_pk(circuit_name),
                   range_key=format_circuit_sk(circuit_name),
                   circuit_state=None,
                   last_state_chg_time=None,
                   failures=0)
    repo.save()
    return repo


def update_circuit(domain, repo: Circuit) -> Circuit:
    repo.failures = domain.failures
    repo.last_state_chg_time = domain.last_state_chg_time
    repo.circuit_state = domain.circuit_state
    repo.save()
    return repo


@monad.monadic_try("find_circuit_by_id", error_cls=DynamoError)
def find_circuit_by_id(id):
    return DB.get(format_circuit_pk(id), format_circuit_sk(id))


def format_circuit_pk(name):
    return ("CIR#" + "{}").format(name)


def format_circuit_sk(name):
    return ("CIR#" + "{}").format(name)
