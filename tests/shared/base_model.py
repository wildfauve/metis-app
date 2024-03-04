from pynamodb.models import Model
from pynamodb.attributes import (
    UnicodeAttribute, NumberAttribute, UnicodeSetAttribute, UTCDateTimeAttribute, DiscriminatorAttribute
)

class BaseModel(Model):
    """
    Base Model consisting of the single table convention; the hash and range keys named PK and SK respectively.
    """
    class Meta:#(Model.Meta):
        table_name = 'base-model'
        region = 'us-east-1'
        # write_capacity_units = 10
        # read_capacity_units = 10
    PK = UnicodeAttribute(hash_key=True)
    SK = UnicodeAttribute(range_key=True)
    kind = DiscriminatorAttribute()

class Circuit(BaseModel, discriminator='Circuit'):
    circuit_state = UnicodeAttribute(null=True)
    last_state_chg_time = UTCDateTimeAttribute(null=True)
    failures = NumberAttribute(null=True)
