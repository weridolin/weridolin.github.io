## drf中的view类
drf中的view是对原生django的view类的一个继承封装.在其基础上封装了一些属性.主要可以分为. APIView.GenericView.一些接口混合类.

### APIView
APIView继承于django的View,对Request和Response进一层封装。相比于原生的django的原生view类型.提供了一下几个基本属性：   

- a.render_class: 响应类型,包含于响应头中 
- b.parse_class: 根据请求的"content-type"字段,选择不同的方式去解析request.body. 
- c.authentication_class:身份认证,通过的话会生成user实例.   
- d.throttle_class:访问频率限制.   
- e.permission_class:权限类.一般先验证身份,在验证权限   
- f.content_negotiation_class:  
- g.metadata_class: 设置options方法返回的一些接口信息
- h:versioning_class:


### Generic views
Generic views继承于APIView，在其基础上在扩充了属性.主要为：
a.queryset:api操作的数据集合 
b.serializer_calss:序列化类方法 
c. lookup_field / lookup_url_kwarg.设置url的query参数 
d.filter_backends:数据过滤类 f.pagination_class:数据查询结果分页.