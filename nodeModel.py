import copy
import json

from model import nodeParamModel
from util import SingleIdUtil
from util.logHandler import logger
from util.Dict_util import sub_global


class Node:
    """
    组件实例类
    """

    def __init__(self, _id, name="", moduleid="", codeName="", template="", desc="", customAttr=None, is_enable=True,
                 inputs=None,
                 outputs=None, flowId=None, unfold=True, self_enable=None):
        # ID
        self._id = _id
        # 实例名称
        self.name = name
        # 组件ID
        self.moduleid = moduleid
        # 方法名称
        self.codeName = codeName
        # 快速修改变量的模版
        self.template = template
        # 用户描述/备注
        if moduleid == 'b9f6a154-8555-11eb-8328-d86b0360bae7' and (not desc):
            self.desc = '#'
        else:
            self.desc = desc
        # 是否有效
        self.is_enable = is_enable
        # 输入参数
        self.inputs = [nodeParamModel.tranDictToNodeParam(_data, self._id) for _data in inputs] if isinstance(inputs,
                                                                                                              list) else []
        # 输出参数
        self.outputs = [nodeParamModel.tranDictToNodeParam(_data, self._id) for _data in outputs] if isinstance(outputs,
                                                                                                                list) else []
        # 自定义属性
        if customAttr is None:
            customAttr = {}
        self.customAttr = customAttr

        # "折叠"组件是否展开状态(默认展开)
        self.unfold = unfold

        # 用于储存当前的注释记录（默认为空）
        if self_enable is None:
            self.self_enable = is_enable
        else:
            self.self_enable = self_enable

        # 用于判断当前是否在注释的容器中

    @staticmethod
    def keys():
        return '_id', 'name', 'moduleid', 'codeName', 'template', 'desc', 'is_enable', 'inputs', 'outputs', 'customAttr', 'unfold', 'self_enable'

    def __getitem__(self, item):
        return getattr(self, item)

    def todict(self):
        _dict = dict(self)
        _dict["inputs"] = [dict(_data) for _data in self.inputs]
        _dict["outputs"] = [dict(_data) for _data in self.outputs]
        return _dict

    def getInputValueByName(self, name):
        for _input in self.inputs:
            # print(_input.name)
            if _input.name == name:
                return _input.value
        raise Exception("找不到相对应的Input值")

    def getInputObjByName(self, name):
        for _input in self.inputs:
            # print(_input.name)
            if _input.name == name:
                return _input
        raise Exception("找不到相对应的Input值")

    def getnodeParamById(self, paramId):
        for _paramType in [self.inputs, self.outputs]:
            for _param in _paramType:
                if _param.judgeidIsEqual(paramId):
                    return _param
        # return None
        raise Exception("根据ParamId未找到对象")

    def transToNewNode(self, flowId, prefixNodeId=None, count=1):
        # 赋予新的NodeId
        oldId = self._id
        newId = SingleIdUtil.getUUID()
        self._id = newId
        shiftcount = 0

        for _paramType in [self.inputs, self.outputs]:
            for _param in _paramType:
                _param.makeNewId(newId)
        return newId

    def judgeidIsEqual(self, nodeId):
        """
        判断Id是否一致
        :param nodeId: 传入的Id
        :return: 判断值
        """
        return self._id == nodeId

    def getEnNameValuePair(self):
        _dict = {}
        for _input in self.inputs:
            _dict[_input.name] = _input.value
        return _dict

    def getCoordinate(self):
        graphData = self.customAttr.get("graphData", None)
        if graphData is None:
            return None, None
        _data = graphData.get(self._id, None)
        if _data is None:
            return None, None
        return _data["x"], _data["y"]

    def makeCode(self, needPass=False, spaceTime=0, filling=None, returnDict=None, global_var=None, moduleDefine=None):
        """
        生成一行代码
        :param global_var [<model.globalVariableModel.globalVariable>]
        :return:
        """
        # TODO 注意是否有三级联动
        # 先查询module定义
        # logger.info(self.__dict__)
        arr = []
        # 先将用户备注添加进去 组件的命令行备注
        if self.desc != "":
            if self.name == "注释":
                desc_lsit = self.desc.split('\n')
                arr.append("    " * spaceTime + "#" * 20)
                for desc in desc_lsit:
                    arr.append("    " * spaceTime + f"# {desc}")
                arr.append("    " * spaceTime + "#" * 20)
            else:
                desc_lsit = self.desc.split('\n')
                for desc in desc_lsit:
                    arr.append("    " * spaceTime + f"# {desc}")
        # 特殊处理
        if self.name == "注释":
            # 不需做处理
            pass
        elif self.name == "else":
            arr.append("    " * (spaceTime) + "else:")
        elif self.name == "elseLoop":
            arr.append("    " * (spaceTime) + "else:")
        elif self.name == "条件分支":
            if_condition = self.getInputValueByName("ifcondition")
            # if 组件 自定义模式
            if "#custom_mode" in if_condition:
                line_value = if_condition.split("#custom_mode")
                is_str = valueIsStr(line_value[0])
                line_code = 'if {}:'.format(line_value[0])
                the_code = sub_global(line_code, [_gv['name'] for _gv in global_var]) if not is_str else line_code
                arr.append("    " * spaceTime + the_code)
            else:
                # if组件向导模式
                if_condition = self.getInputValueByName("ifcondition")
                if not if_condition:
                    rul_list = ''
                else:
                    rul_list = get_if_rules(if_condition, global_var)
                line_code = "if " + ''.join(rul_list) + ":"
                arr.append("    " * spaceTime + line_code)
        elif self.name == "elif":
            elif_condition = self.getInputValueByName("elifcondition")
            # if 组件 自定义模式
            # if self.is_enable:
            #     arr.append("    " * spaceTime + "pass")
            if "#custom_mode" in elif_condition:
                line_value = elif_condition.split("#custom_mode")
                is_str = valueIsStr(line_value[0])
                line_code = 'elif {}:'.format(line_value[0])
                the_code = sub_global(line_code, [_gv['name'] for _gv in global_var]) if not is_str else line_code
                arr.append("    " * (spaceTime) + the_code)
            else:
                # if组件向导模式
                elif_condition = self.getInputValueByName("elifcondition")
                if not elif_condition:
                    rul_list = ''
                else:
                    rul_list = get_if_rules(elif_condition, global_var)
                line_code = "elif " + ''.join(rul_list) + ":"
                arr.append("    " * (spaceTime) + line_code)

        elif self.name == "循环控制":
            for _input in self.inputs:
                logger.debug(_input.__dict__)
            lp_type = self.getInputValueByName("looptype")  # 记录类型
            lp_condition = copy.deepcopy(self.getInputValueByName("loopcondition"))  # 循环所需的 索引 被循环值 或条件

            if isinstance(lp_condition, list):
                # lp_condition 为数组
                if len(lp_condition) < 4:
                    # 且不满4位
                    while len(lp_condition) < 4:
                        lp_condition.append("")
            else:
                # 初始化为数组
                lp_condition = ["", "", "", ""]

            # for循环
            if lp_type == 'for_list':  # 遍历数组
                list_is_str = valueIsStr(lp_condition[2])
                list_code = sub_global(lp_condition[2], [_gv['name'] for _gv in global_var]) if not list_is_str else \
                    lp_condition[2]
                if lp_condition[1] == "":
                    # print('没有索引')
                    line_code = 'for {item} in {list}:'.format(item=lp_condition[0], list=list_code)
                else:
                    line_code = 'for {index},{item} in enumerate({list}):'.format(item=lp_condition[0],
                                                                                  index=lp_condition[1], list=list_code)
                arr.append("    " * spaceTime + line_code)
            # 遍历字典
            elif lp_type == 'for_dict':
                dict_is_str = valueIsStr(lp_condition[2])
                dict_code = sub_global(lp_condition[2], [_gv['name'] for _gv in global_var]) if not dict_is_str else \
                    lp_condition[2]
                line_code = 'for {k}, {v} in {dt}.items():'.format(k=lp_condition[0], v=lp_condition[1],
                                                                   dt=dict_code)
                # the_code = sub_global(line_code, [_gv['name'] for _gv in global_var]) if "'" not in line_code or '"' not in line_code else line_code
                arr.append("    " * spaceTime + line_code)
            # 计次循环
            elif lp_type == 'for_times':
                start_is_str = valueIsStr(lp_condition[1])
                end_is_str = valueIsStr(lp_condition[2])
                step_is_str = valueIsStr(lp_condition[3])
                start_code = sub_global(lp_condition[1], [_gv['name'] for _gv in global_var]) if not start_is_str else \
                    lp_condition[1]
                end_code = sub_global(lp_condition[2], [_gv['name'] for _gv in global_var]) if not end_is_str else \
                    lp_condition[2]
                step_code = sub_global(lp_condition[3], [_gv['name'] for _gv in global_var]) if not step_is_str else \
                    lp_condition[3]

                line_code = 'for {index} in range({start}, {end}, {step}):'.format(index=lp_condition[0],
                                                                                   start=start_code,
                                                                                   step=step_code,
                                                                                   end=end_code)
                # the_code = sub_global(line_code, [_gv['name'] for _gv in global_var]) if "'" not in line_code or '"' not in line_code else line_code
                arr.append("    " * spaceTime + line_code)
            # while
            else:
                logger.info('loop in here')
                lp_condition = self.getInputValueByName("loopcondition")
                if "#custom_mode" in lp_condition:  # 自定义模式
                    line_value = lp_condition.split('#custom_mode')
                    is_str = valueIsStr(line_value[0])
                    code = sub_global(line_value[0],
                                      [_gv['name'] for _gv in global_var]) if not is_str else line_value[0]

                    line_code = "while {}:".format(code)
                    # arr.append("    " * spaceTime + line_code)
                else:  # 向导模式
                    if not lp_condition:
                        rul_list = ''
                    else:
                        rul_list = get_if_rules(lp_condition, global_var)
                    line_code = 'while ' + ''.join(rul_list) + ':'
                arr.append("    " * spaceTime + line_code)
            # if needPass:
            #     arr.append("    " * (spaceTime + 1) + "pass")

        elif self.name == "跳出循环":
            arr.append("    " * spaceTime + "break")

        elif self.name == "继续循环":
            arr.append("    " * spaceTime + "continue")

        elif self.name == "异常捕获":
            arr.append("    " * spaceTime + f"try:")

        elif self.name == "catch":
            value = filling.get()
            arr.append("    " * spaceTime + f"except Exception as {value['value']}:")

        elif self.name == "finally":
            arr.append("    " * spaceTime + "finally:")

        elif self.name in ["endIf", "endtry", "endLoop"]:
            # if self.is_enable:
            #     arr.append("    " * (spaceTime + 1) + "pass")
            arr.append("    " * spaceTime + f"# {self.name}")

        elif self.name == "流程块返回":
            line = "    " * spaceTime + "return " + ",".join(returnDict.keys())
            new_line = sub_global(line, [_gv['name'] for _gv in global_var])
            arr.append(new_line)
        elif self.name == "变量赋值":
            # 对象
            varValueObj = self.getInputObjByName("init")

            # 变量名
            varName = self.getInputValueByName("newVar")
            varName = varName.replace('\n', '') if isinstance(varName, str) else varName
            value = varValueObj.getValue(glv=global_var)
            value_line = None
            # 如果全局变量中有相同的变量名，不管isGlobal 直接等价
            if global_var:
                # logger.info(global_var)
                var_name = sub_global(varName, [_gv['name'] for _gv in global_var])
                value_line = "    " * spaceTime + f"{var_name} = {value}"
            if not value_line:
                value_line = "    " * spaceTime + f"{varName} = {value}"
            arr.append(value_line)

        elif self.name == "打印日志":
            # 日志等级
            loggerLevel = self.getInputValueByName("logLevel")
            template_obj = self.getInputObjByName("template_string")
            replaceType = self.getInputValueByName("replaceType")
            template_string = template_obj.getValue(glv=global_var)

            # 替换内容
            params = self.getInputValueByName("params")

            if params:
                if global_var:
                    param_inputs = self.getInputObjByName("params")
                    param_is_str = valueIsStr(params)
                    if param_inputs.valueType == "python":
                        params = sub_global(params, [_gv['name'] for _gv in global_var]) if not param_is_str else params
                arr.append(
                    "    " * spaceTime + f"logger.{str(loggerLevel)}({template_string}.{str(replaceType)}({params}), exc_info=True)")
            else:
                arr.append("    " * spaceTime + f"logger.{str(loggerLevel)}({template_string}, exc_info=True)")
        elif self.name == "延迟":
            delay = self.getInputValueByName("delay")
            arr.append("    " * spaceTime + f"time.sleep({delay})")
        elif self.name == "自定义代码块":
            _codeString = self.getInputValueByName("自定义代码块")
            for _codeLine in _codeString.split("\n"):
                arr.append("    " * spaceTime + str(_codeLine))
            # 普通的组件生成规则
        else:
            # moduleDefine = moduleModel.queryByModuleId(self.moduleid)
            try:
                # 将input的json字符串转为数组字典对象

                inputs = json.loads(moduleDefine.input) if isinstance(moduleDefine.input, str) else moduleDefine.input
            except Exception as e:
                logger.error(moduleDefine.input)
                logger.error(f"{self.name} 定义的输入参数非json字符串,转换失败!")
                raise e

            # 定义的keyvalue
            define_enNameValuePair = moduleDefine.getEnNameValuePair()
            # model input 的key value
            node_enNameValuePair = self.getEnNameValuePair()

            # 生成默认的规则
            if 'self-' in self.moduleid:
                module_name = self.codeName.split('.')[0]
                arr.append("    " * spaceTime + f"import {module_name}")
                funcName = str(self.codeName)
            else:
                funcName = "sendiRPA." + str(self.codeName)
            # 生成input

            # 遍历model
            inputs_arr = []
            for _nodeParam in self.inputs:
                # 记录是否渲染input
                needMake = True
                componentType = 0
                # 遍历定义的input数组
                for moduleInputDefine in inputs:
                    # 判断名字是否相等
                    if moduleInputDefine['enName'] == _nodeParam.name:
                        componentType = moduleInputDefine["componentType"]
                        # 判断parentLink是否为空
                        """ 入参的翻译，当含有parent进入了第一个条件Link(代表该层为某一层二级联动的结果)时：parentLink = {enName:xx, value:True},
                            即 input['name'] = xx & input['value']对应的 value = True时，该层有效并将被前端渲染展示，后台同步翻译，
                            当value = False时，后台不翻译该入参的结果（使用组件自己的默认值）"""
                        if isinstance(moduleInputDefine["parentLink"], dict) and moduleInputDefine["parentLink"] != {}:
                            # 判断enName的value 是否与node 的value是否一致
                            enName = moduleInputDefine["parentLink"]["enName"]
                            if isinstance(moduleInputDefine["parentLink"]["value"], list):
                                if node_enNameValuePair[enName] not in moduleInputDefine["parentLink"]["value"]:
                                    needMake = False
                                    break
                            else:
                                if node_enNameValuePair[enName] != moduleInputDefine["parentLink"]["value"]:
                                    needMake = False
                                    break

                # 如果需要渲染到代码中,则添加到数组
                if needMake:
                    inputs_arr.append(
                        _nodeParam.makeInputCode(componentType=componentType,
                                                 glv=global_var))  # 返回 [n1=v1, n2=glv['v2'], n3=v3]

            inputStr = ", ".join(inputs_arr)
            if funcName == 'sendiRPA.workProcess.run':
                inputStr += ", glv=glv"
            if len(self.outputs):
                output_list = []
                # 调用子流程的根据出参入参进行翻译
                for _nodeParam in self.outputs:
                    if _nodeParam.value != '':
                        _str = f"{_nodeParam.value}"
                    else:
                        _str = '_'
                    _str = sub_global(_str, [_gv['name'] for _gv in global_var])
                    output_list.append(_str)
                outputStr = ", ".join(output_list)  # ''=global[''] if '' in global.keys() else ''
                arr.append("    " * spaceTime + f"{outputStr}={funcName}({inputStr})")

            else:
                arr.append("    " * spaceTime + f"{funcName}({inputStr})")

        if not self.is_enable:
            arr = [line.replace('\n', '\n#') for line in arr]
            arr = ["    " * spaceTime + "#" + _line for _line in arr]

        node_arr = [{self._id: arr_element} for arr_element in arr]
        return node_arr


def transdictToNode(data, flowId):
    return Node(
        _id=data['_id'],
        name="" if 'name' not in data.keys() else data['name'],
        moduleid="" if 'moduleid' not in data.keys() else data['moduleid'],
        codeName="" if 'codeName' not in data.keys() else data['codeName'],
        template="" if 'template' not in data.keys() else data['template'],
        desc="" if 'desc' not in data.keys() else data['desc'],
        is_enable=True if 'is_enable' not in data.keys() else data['is_enable'],
        inputs=[] if 'inputs' not in data.keys() else data['inputs'],
        outputs=[] if 'outputs' not in data.keys() else data['outputs'],
        customAttr={} if 'customAttr' not in data.keys() else data['customAttr'],
        flowId=flowId,
        self_enable=None if 'self_enable' not in data.keys() else data['self_enable'],
    )


def getNodeById(nodeId) -> Node:
    from initFlask import StateManage
    # TODO 当前还有导入旧版本流程和自定义代码在引用，
    if nodeId not in StateManage.nodeToFlow.keys():
        StateManage.loadAllData()
        # raise Exception("根据NodeID未找到对应流程")
    flowId = StateManage.nodeToFlow[nodeId]
    model = StateManage.memoryModel[flowId]
    return model.queryNodeById(nodeId)


def get_if_rules(cond, glv=None):
    # 对于if容器的特殊翻译
    rule_lst = []
    try:
        cond = json.loads(cond)
        for index, item in enumerate(cond):
            v1_is_str = valueIsStr(item['value1'])
            v2_is_str = valueIsStr(item['value2'])
            v1 = sub_global(item['value1'], [_gv['name'] for _gv in glv]) if not v1_is_str else item['value1']
            v2 = sub_global(item['value2'], [_gv['name'] for _gv in glv]) if not v2_is_str else item['value2']
            if item['rules'].lower() in ["is false", "is true", "is none", "is not none"]:
                # 只有value1 有效，value2不可进入翻译内容
                rule_lst.append("({lft} {rule})".format(lft=v1, rule=item['rules']))
            elif item['rules'].lower() in ["in", "not in"]:
                rule_lst.append(
                    "({lft} {rule} {rgt})".format(lft=v2, rule=item['rules'], rgt=v1))
            else:
                # if value1 rule value2
                rule_lst.append(
                    "({lft} {rule} {rgt})".format(lft=v1, rule=item['rules'], rgt=v2))
            if index != len(cond) - 1:
                # pipe 为 &、or，当条件只有一个 或最后一个，不需要当前的pipe
                rule_lst.append(' or ' if item['pipe'] == 0 else ' and ')
        return rule_lst
    except Exception as e:
        return rule_lst


def valueIsStr(value):
    try:
        _ = json.loads(value)
        is_str = True
    except Exception as e:
        # logger.info(f'{e}:正常处理，忽略(当前变量框含变量)')
        is_str = False
    return is_str
