import asyncio
import time
import uvicorn
import h11
async def async_app(scope,receive,send):
    print("get scope >>>",scope)
    event = await receive()
    print("get event >>>",event)
    # await asyncio.sleep(10)
    await send({
            'type': 'http.response.start',   # 响应头的信息通过这个事件返回，必须发生在body发送之前
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
        ]   # 发送响应体内容事件
    })
    await send({
        'type': 'http.response.body',   # 发送响应体内容事件
        'body': "response part1".encode("utf-8"),
        'more_body': True  # 代表后面还有消息要返回
    })
    # await asyncio.sleep(3) # 不能使用time.sleep, 会阻塞整个线程
    await send({
        'type': 'http.response.body',
        'body': "response part2".encode("utf-8"),
        'more_body': False # 已经没有内容了，请求可以结束了
    })
    # event = await receive()
    print("get event >>>",event)



async def app2(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            print(f'get message -->  {message}')
            if message['type'] == 'lifespan.startup':
                ... # Do some startup here!
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                ... # Do some shutdown here!
                await send({'type': 'lifespan.shutdown.complete'})
                return
            else:
                await send({
                    'type': 'http.response.start',   # 响应头的信息通过这个事件返回，必须发生在body发送之前
                    'status': 200,
                    'headers': [
                        [b'content-type', b'application/json'],
                ]   # 发送响应体内容事件
                })
                await send({
                    'type': 'http.response.body',   # 发送响应体内容事件
                    'body': "response part1".encode("utf-8"),
                    'more_body': True  # 代表后面还有消息要返回
                })
                # await asyncio.sleep(3) # 不能使用time.sleep, 会阻塞整个线程
                await send({
                    'type': 'http.response.body',
                    'body': "response part2".encode("utf-8"),
                    'more_body': False # 已经没有内容了，请求可以结束了
            })
    else:
        pass # Handle other types