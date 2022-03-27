
import typing as t
class TEST(object):
    def __getattr__(self, name: str) -> t.Any:
        print("get attr name",name)

    def __setattr__(self, name: str, value: t.Any) -> None:
        print("set attr",name,value)


TEST().EE=22       
