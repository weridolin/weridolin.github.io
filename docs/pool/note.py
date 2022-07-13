import threading

ctx = threading.local()
ctx.var1="Var1"
ctx.var2="Var2"
print(ctx.__dict__)

def f():
    # ctx.var1="Var11"
    # ctx.var2="Var22"
    print(ctx)
    print(ctx.__dict__)

threading.Thread(target=f).start()

print(ctx._local__impl)