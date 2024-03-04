import json
import decimal
import pendulum


class CustomLogEncoder(json.JSONEncoder):
    def default(self, obj):
        match type(obj):
            case pendulum.DateTime:
                return obj.to_iso8601_string()
            case decimal.Decimal:
                return str(obj)
            case _:
                breakpoint()
                return json.JSONEncoder.default(self, obj)