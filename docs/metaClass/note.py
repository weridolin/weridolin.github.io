class Field():
    A =  1

    def __set__(self,instance,value):
        print("set",self,instance,value)
        ...

    def __get__(self,instance,cls_type):
        if instance:
            print(instance.__dict__,"instance is not None")
        if cls_type:
            print("cls type is not None")
        print("get",self,instance,cls_type)
        ...



class Test:
    attr = Field()

    def __init__(self) -> None:
        self.attr=2
        ...


# print(Test.attr,Test().attr)
print(Test.attr,Test().attr)

# class Type2(type):

#     def __new__(cls, name, bases, attrs, **kwargs):
#         print(name,bases,attrs,kwargs)
#         return super().__new__(cls, name, bases, attrs, **kwargs)


# from django.db import models

# class Test2(metaclass=Type2):
#     var1=models.IntegerField()

#     class Meta:
#         a = 1

#     def __init__(self,var=None) -> None:
#         self.var1=2

# print(dir(Test2.var1))
# Test2(var=1)