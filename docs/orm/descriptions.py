class Descriptions:

    def __set__(self, instance, value):
        print(">>> set class descriptions value", instance, value)

    def __get__(self, instance, cls):
        print(">>> get class description value", instance, cls)
        return "get class description value"


class TestObject:
    instance_value = Descriptions()
    # instance_value = "Sss"

    def __init__(self) -> None:
        self.instance_value = 222


T = TestObject()
print(T.instance_value)
print(T.instance_value)
T.instance_value = 222


l1 = [{"key":1,"value":2},{"key":2,"value":3}]
l2 = [{"key":1,"value":3},{"key":2,"value":4}]  