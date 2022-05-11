from  functools import partial

### 不接受kwargs接收kwargs的方法
def exec(callback,*args):
    callback(*args)

def test(callback,*args,**kwargs):
    _func = partial(callback,**kwargs)
    return exec(_func,*args)

def test_callback(*args,**kwargs):
    print(args,kwargs)

if __name__ == "__main__":
    test(test_callback,3,4,kw1=3,kw2=4)
