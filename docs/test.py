class TEST:
    VAR1 = 2
    VAR2 = 3
    def __init__(self,VAR1) -> None:
        self.VAR1=VAR1
        print(self.VAR1,TEST.VAR1)
t = TEST(22)
print(t.VAR2)
setattr(t,"VAR2",333)
print(t.VAR2,TEST.VAR2)