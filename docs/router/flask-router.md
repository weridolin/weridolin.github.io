## flask-route中的路由匹配逻辑。
在`python`的`web`开发中，路由是定义一个请求和处理方法之间联系的方法.当请求进来时,web框架根据`url path`在已经注册的 `endpoint(url-path)`-`func`map中找到对应的`func`,并返回其处理结果.下面从源码简单理解下``路由注册``和``请求链接到处理函数``的过程.



### 路由定义在flask的储存格式
每个`flask-app`的所有路由都会存在一个`state`对象里面,`state`的结构如下:

```python

class State:
    """A representation of a rule state.

    This includes the *rules* that correspond to the state and the
    possible *static* and *dynamic* transitions to the next state.
    """

    dynamic: list[tuple[RulePart, State]] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    static: dict[str, State] = field(default_factory=dict) # 静态路由


```


##### 静态路由
所有的静态路由都会储存在`state`的`static`中,每个`url_path`会被会按`/`分割成一个`parts`列表.从第一级开始,依次`嵌套`存储在`state`实例中的`static`中.`static`的中的`key`为`part`.

例如:

假设有两个url:`/aa/bb/cc`,`/aa/bb/dd/`.对应的`view function`为`cc_deal`,`dd_deal` 则储存到`State`中的结构为:

```python

State(
    static={
        "aa":Static(
            static={
                "bb":Static(
                    static:{
                        "cc":Static(
                            static:{} ## 不以 “/”结尾，这里已经结束
                            rule:["cc_deal"]
                        ),
                        "dd":Static(
                            static:{ ## 以 “/”结尾，最后还有一层key为" "的嵌套
                                "":Static(
                                    static:{} ## 
                                    rule:["dd_deal"]
                                )
                            }
                        )

                    }
                )
            }
        )
    }

)


```

请求到来时,每个`url_path`会被会按`/`分割成一个`parts`列表.按各个`part`依次从 state 往里面找,知道找到对应的 `view_func`.对应的代码如下:


```python

    def match(
        self, domain: str, path: str, method: str, websocket: bool
    ) -> tuple[Rule, t.MutableMapping[str, t.Any]]:
        # To match to a rule we need to start at the root state and
        # try to follow the transitions until we find a match, or find
        # there is no transition to follow.

        have_match_for = set()
        websocket_mismatch = False


        def _match(
            state: State, parts: list[str], values: list[str]
        ) -> tuple[Rule, list[str]] | None:
            # This function is meant to be called recursively, and will attempt
            # to match the head part to the state's transitions.
            nonlocal have_match_for, websocket_mismatch
            # The base case is when all parts have been matched via
            # transitions. Hence if there is a rule with methods &
            # websocket that work return it and the dynamic values
            # extracted.
            ## parts : /a/b/c -> [a,b,c]
            if parts == []: ## 如果路径匹配最后会执行这里
                for rule in state.rules:## 根路径对应的 view func
                    if rule.methods is not None and method not in rule.methods:
                        have_match_for.update(rule.methods)
                    elif rule.websocket != websocket:
                        websocket_mismatch = True
                    else:
                        return rule, values

                # Test if there is a match with this path with a
                # trailing slash, if so raise an exception to report
                # that matching is possible with an additional slash
                if "" in state.static:
                    for rule in state.static[""].rules:
                        if websocket == rule.websocket and (
                            rule.methods is None or method in rule.methods
                        ):
                            if rule.strict_slashes: ## 没有 ”/“,抛出异常
                                raise SlashRequired()
                            else:
                                # 否则自动返回 根路径 ”/“对应的 view_func
                                return rule, values
                return None

            part = parts[0]
            # To match this part try the static transitions first
            ## static.static 
            ##  /a/b/c ->
            ## {'aa': 
                # State(dynamic=[], rules=[], static={
                #     'bb': State(dynamic=[], rules=[], static={
                #         'cc': State(dynamic=[], rules=[], static={
                #             'dd': State(dynamic=[], rules=[<Rule '/aa/bb/cc/dd' -> special>], static={
                #             })})})}
            ## 
            if part in state.static:
                ## 根据 parts列表逐个往里面 state里面查找,如果已经匹配到最后一个，传入[]
                rv = _match(state.static[part], parts[1:], values)
                if rv is not None:
                    return rv
            # No match via the static transitions, so try the dynamic
            # ones.
            for test_part, new_state in state.dynamic:
                target = part
                remaining = parts[1:]
                # A final part indicates a transition that always
                # consumes the remaining parts i.e. transitions to a
                # final state.
                if test_part.final:
                    target = "/".join(parts)
                    remaining = []
                match = re.compile(test_part.content).match(target)
                if match is not None:
                    if test_part.suffixed:
                        # If a part_isolating=False part has a slash suffix, remove the
                        # suffix from the match and check for the slash redirect next.
                        suffix = match.groups()[-1]
                        if suffix == "/":
                            remaining = [""]

                    converter_groups = sorted(
                        match.groupdict().items(), key=lambda entry: entry[0]
                    )
                    groups = [
                        value
                        for key, value in converter_groups
                        if key[:11] == "__werkzeug_"
                    ]
                    rv = _match(new_state, remaining, values + groups)
                    if rv is not None:
                        return rv

            # If there is no match and the only part left is a
            # trailing slash ("") consider rules that aren't
            # strict-slashes as these should match if there is a final
            # slash part.
            if parts == [""]: # 根路径 ”/“对应的 view_func
                for rule in state.rules:
                    if rule.strict_slashes:
                        continue
                    if rule.methods is not None and method not in rule.methods:
                        have_match_for.update(rule.methods)
                    elif rule.websocket != websocket:
                        websocket_mismatch = True
                    else:
                        return rule, values

            return None

        
        ## 这里的__root就是生成的一个 state 实例
        try:
            rv = _match(self._root, [domain, *path.split("/")], [])
        except SlashRequired:
            raise RequestPath(f"{path}/") from None

        if self.merge_slashes and rv is None:
            # Try to match again, but with slashes merged
            path = re.sub("/{2,}?", "/", path)
            try:
                ## 按照分割的 parts列表逐个返回
                rv = _match(self._root, [domain, *path.split("/")], [])
            except SlashRequired:
                raise RequestPath(f"{path}/") from None
            if rv is None or rv[0].merge_slashes is False:
                raise NoMatch(have_match_for, websocket_mismatch)
            else:
                raise RequestPath(f"{path}")
        elif rv is not None:
            rule, values = rv

            result = {}
            for name, value in zip(rule._converters.keys(), values):
                try:
                    value = rule._converters[name].to_python(value)
                except ValidationError:
                    raise NoMatch(have_match_for, websocket_mismatch) from None
                result[str(name)] = value
            if rule.defaults:
                result.update(rule.defaults)

            if rule.alias and rule.map.redirect_defaults:
                raise RequestAliasRedirect(result, rule.endpoint)

            return rule, result

        raise NoMatch(have_match_for, websocket_mismatch)



```

拿`/aa/bb/cc/ff`举例子, `_match`递归调用处理的`part`依次为: 

``` python

['aa', 'bb', 'cc', 'ff']
['bb', 'cc', 'ff']
['cc', 'ff']
['ff']
[]

最终进入到 `part==[]`的判断逻辑,并返回对应的`view_func`

```


##### 动态路由

当`url`中含有 path 参数时,带`path`参数部分会被存储在`state`中的`dynamic`中，而非`static`.

例如:路径`/<int:name>/silly/<path:name2>/edit`,则对应在`state`中的结构为:

```python 

State(
  dynamic=[], 
  rules=[], 
  static={'': 
    State(  
    dynamic=[], 
    rules=[], 
    static={
      '': State(
        dynamic=[
          (
            RulePart(
                content='(?P<__werkzeug_0>\\d+)\\Z', 
                final=False, 
                static=False, 
                suffixed=False, 
                weight=Weighting(number_static_weights=0, static_weights=[], number_argument_weights=-1, argument_weights=[50])),
                State(
                  dynamic=[], 
                  rules=[], 
                  static={
                    'silly': State(
                      dynamic=[
                        (RulePart(content='(?P<__werkzeug_0>[^/].*?)/edit\\Z', final=True, static=False, suffixed=False, weight=Weighting(number_static_weights=-1, static_weights=[(0, -4)], number_argument_weights=-1, argument_weights=[200])), 
                        State(
                          dynamic=[], 
                          rules=[<Rule '/<name>/silly/<name2>/edit' -> editsillypage>], static={}))], rules=[], static={})}))
                          ], 
                      rules=[], 
                      static={})})
                      }
                )

```

和`static`静态路由类似.动态路由中涉及正则匹配的`part`会被存储在`state`中的`dynamic`字段中.匹配过程中如果在`static`字段匹配不到时，会自动在`dynamic`列表中查找匹配，在`/<int:name>/silly/<path:name2>/edit`首先先匹配第一部分`<int:name>`,对应的正则表达式为`(?P<__werkzeug_0>\\d+)\\Z`,接着在匹配到的`State`实例中的`static`找到`silly`对应的`state`实例.再在其中的`dynamic`找到`<path:name2>/edit`对应的匹配表达式`(?P<__werkzeug_0>[^/].*?)/edit\\Z`.

```python

    def match(
        self, domain: str, path: str, method: str, websocket: bool
    ) -> tuple[Rule, t.MutableMapping[str, t.Any]]:
        # To match to a rule we need to start at the root state and
        # try to follow the transitions until we find a match, or find
        # there is no transition to follow.

        have_match_for = set()
        websocket_mismatch = False


        def _match(
            state: State, parts: list[str], values: list[str]
        ) -> tuple[Rule, list[str]] | None:
            # This function is meant to be called recursively, and will attempt
            # to match the head part to the state's transitions.
            nonlocal have_match_for, websocket_mismatch
            # The base case is when all parts have been matched via
            # transitions. Hence if there is a rule with methods &
            # websocket that work return it and the dynamic values
            # extracted.
            ## parts : /a/b/c -> [a,b,c]
            if parts == []: ## 如果路径匹配最后会执行这里
                for rule in state.rules:
                    if rule.methods is not None and method not in rule.methods:
                        have_match_for.update(rule.methods)
                    elif rule.websocket != websocket:
                        websocket_mismatch = True
                    else:
                        return rule, values

                # Test if there is a match with this path with a
                # trailing slash, if so raise an exception to report
                # that matching is possible with an additional slash
                if "" in state.static:
                    for rule in state.static[""].rules:
                        if websocket == rule.websocket and (
                            rule.methods is None or method in rule.methods
                        ):
                            if rule.strict_slashes:
                                raise SlashRequired()
                            else:
                                return rule, values
                return None

            part = parts[0]
            # To match this part try the static transitions first
            ## static.static 
            ##  /a/b/c ->
            ## {'aa': 
                # State(dynamic=[], rules=[], static={
                #     'bb': State(dynamic=[], rules=[], static={
                #         'cc': State(dynamic=[], rules=[], static={
                #             'dd': State(dynamic=[], rules=[<Rule '/aa/bb/cc/dd' -> special>], static={
                #             })})})}
            ## 
            if part in state.static:
                rv = _match(state.static[part], parts[1:], values)
                if rv is not None:
                    return rv
            
            ## 静态路由匹配不到，才尝试匹配动态路由
            # No match via the static transitions, so try the dynamic
            # ones.
            for test_part, new_state in state.dynamic:
                target = part
                remaining = parts[1:]
                # A final part indicates a transition that always
                # consumes the remaining parts i.e. transitions to a
                # final state.
                if test_part.final:
                    target = "/".join(parts)
                    remaining = []
                match = re.compile(test_part.content).match(target)
                if match is not None:
                    if test_part.suffixed:
                        # If a part_isolating=False part has a slash suffix, remove the
                        # suffix from the match and check for the slash redirect next.
                        suffix = match.groups()[-1]
                        if suffix == "/":
                            remaining = [""]

                    converter_groups = sorted(
                        match.groupdict().items(), key=lambda entry: entry[0]
                    )
                    groups = [
                        value
                        for key, value in converter_groups
                        if key[:11] == "__werkzeug_"
                    ]
                    rv = _match(new_state, remaining, values + groups)
                    if rv is not None:
                        return rv

            # If there is no match and the only part left is a
            # trailing slash ("") consider rules that aren't
            # strict-slashes as these should match if there is a final
            # slash part.
            if parts == [""]:
                for rule in state.rules:
                    if rule.strict_slashes:
                        continue
                    if rule.methods is not None and method not in rule.methods:
                        have_match_for.update(rule.methods)
                    elif rule.websocket != websocket:
                        websocket_mismatch = True
                    else:
                        return rule, values

            return None


        try:
            # 这里同样是把待匹配的url按 “/”分割
            rv = _match(self._root, [domain, *path.split("/")], [])
        except SlashRequired:
            raise RequestPath(f"{path}/") from None

        if self.merge_slashes and rv is None:
            # Try to match again, but with slashes merged
            path = re.sub("/{2,}?", "/", path)
            try:
                rv = _match(self._root, [domain, *path.split("/")], [])
            except SlashRequired:
                raise RequestPath(f"{path}/") from None
            if rv is None or rv[0].merge_slashes is False:
                raise NoMatch(have_match_for, websocket_mismatch)
            else:
                raise RequestPath(f"{path}")
        elif rv is not None:
            rule, values = rv

            result = {}  # 路径参数:值
            for name, value in zip(rule._converters.keys(), values):
                try:
                    value = rule._converters[name].to_python(value)
                except ValidationError:
                    raise NoMatch(have_match_for, websocket_mismatch) from None
                result[str(name)] = value
            if rule.defaults:
                result.update(rule.defaults)

            if rule.alias and rule.map.redirect_defaults:
                raise RequestAliasRedirect(result, rule.endpoint)

            return rule, result

        raise NoMatch(have_match_for, websocket_mismatch)
 
```

动态路由匹配的路基跟静态路由一致，就是带正则匹配的会到`dynamic`中.静态路由会匹配到`static`


补充:   
当 `url`带了参数时,比如 `<path:int>`,在添加到`state`实例时会转换为`(?P<__werkzeug_0>\d+)\Z`.
`?P<name>`代表一个命名组.匹配到的内容会赋给`name`
