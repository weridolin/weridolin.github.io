from asyncio.log import logger
import  requests

def wechatGroupRobot(content_type:str,content=None,robot_webhook_uri:str=None,file_path:str= None,**kwargs):
    if content_type not in ["text","file","markdown","image"]:
        raise TypeError("发送内容错误,仅支持文本/markdown文本/文件/图片")
    if content_type == "text":
        logger.debug("正在发送文本到群聊机器人")
        
    elif content_type == "file":
        logger.debug("正在发送文件到群聊机器人")
    elif content_type =="markdown":
        logger.debug("正在发送markdown文本到群聊机器人")
    elif content_type == "image":
        logger.debug("正在发送图片到群聊机器人")
    else:
        raise TypeError("发送内容错误,仅支持文本/markdown文本/文件/图片")
    
