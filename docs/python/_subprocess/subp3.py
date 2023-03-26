import _winapi

print("pipe client")
quit = False

while not quit:
    handle = _winapi.CreateFile(
        r'\\.\pipe\mypipename',
        _winapi.GENERIC_READ | _winapi.GENERIC_WRITE,
        0,
        0,
        _winapi.OPEN_EXISTING,
        0,
        0
    )
    # res = _winapi.SetNamedPipeHandleState(handle, _winapi.PIPE_READMODE_MESSAGE, None, None)
    # if res == 0:
    #     print(f"SetNamedPipeHandleState return code: {res}")
    while True:
        resp = _winapi.ReadFile(handle, 64*1024)
        print(f"message: {resp}")
