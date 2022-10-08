import gevent



def test():
    globals().update({
        "aa":11
    })

def test2():
    print(globals())

if __name__ =="__main__":
    test2()