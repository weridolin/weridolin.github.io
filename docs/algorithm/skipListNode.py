from typing import List, Optional, Any

MAXLEVEL = 32


class SkipListLevel():
    """
        跳表的层级结构索引
    """

    # 指向下个节点
    next: "SkipListNode" = None

    # 索引跨度，到下一个节点经历了多少个节点
    span: int = 0


class SkipListNode():
    """
        跳表的节点结构
    """

    pre_node: "SkipListNode" = None
    level: List["SkipListLevel"] = []  # 跳表层级
    value: Any = None
    score: int = 0  # 跨度，即为节点所在链表的第几个节点


class SkipList():
    """
        跳表链表
    """

    head: SkipListNode = None  # 头节点
    tail: SkipListNode = None  # 尾节点
    length: int = 0  # node的数量
    level: int = 0  # 当前跳表的最大层级
    max_level: int = 0  # 跳表可以达到的最大层级

    def __init__(self, max_level: int = MAXLEVEL):

        self.max_level = max_level
        # 初始化 创建头节点
        self.head = SkipListNode()
        # 创建头节点的各层索引,第一层都是1 头部节点的索引level的层数就是最大层数
        for index, _ in enumerate(range(self.max_level)):
            new = SkipListLevel()
            if index == 0:
                new.span = 1
            self.head.level.append(new)

    def insert(self, value: Any):
        """
            插入新的节点
        """
        # 随机生成新节点的层级
        new_node_level = self.random_level()

        # 创建新节点
        new_node = self.create_node(new_node_level, value)

        # 记录元素查找过程中，每一层跨越的节点数量,比如i=7 代表该节点的第7层索引上个节点上个节点处于的链表中的位置
        rank: List[int] = [0 for _ in range(self.max_level)]
        # 新节点的索引层每一层的上一个节点
        update: List[SkipListNode] = [None for _ in range(self.max_level)]

        # 找寻插入位置
        current_node = self.head

        # 跳表的查询
        for i in range(self.level-1, -1, -1):
            # 计算当前current_node为第几个node,这里的排序是只针对当前level层
            if i == self.level-1:  # 为头节点，为 跳表列表的第一个节点
                rank[i] = 0
            else:
                rank[i] = rank[i+1]

            # 从最高层开始查找
            # 如果查找的当前节点的下个节点的值小于插入的节点的值，则移动到下个节点
            while current_node.level[i].next and current_node.level[i].next.value < value:
                # 记录每一层跨越的节点数量。span为当前索引层到下一个节点之间间隔多少个节点,也就是
                # 新增节点处于current node 的下个节点之后
                # 所以新增节点的 level[i].span 必须加上当前层到下个节点之间的跨度，即为当前节点当前level层的span
                # rank[i]记录当前节点第 i 层的上个节点的所在链表的位置
                rank[i] += current_node.level[i].span
                # 当前节点找到下一个节点
                current_node = current_node.level[i].next

            # 当前节点的下个节点的值大于插入的节点的值，说明当前节点为插入节点的上个节点
            # 记录每一level层的上一个节点
            update[i] = current_node

        # 处理新节点的level大于链表的level的情况
        if new_node_level > self.level:
            for i in range(self.level, new_node_level, 1):
                # 该层索引上个节点为头节点，处于链表第一个位置
                rank[i] = 0
                update[i] = self.head  # 上个节点为头节点

                update[i].level[i].span = 0  # todo

            # 更新链表的最大长度
            self.level = new_node_level

        # 插入新的node,并且更新各个索引曾level对应的上个和下个节点
        for i in range(0, new_node_level, 1):
            update[i].level[i].next = new_node
            new_node.level[i].next = update[i].level[i].next

            # 设置 span #todo


        # 如果新节点的level小于现有的节点的level，则从新节点的level开始更新各个索引层上个节点的span+1(+1是因为插入了新节点)
        for i in range(new_node_level, self.level, 1):
            update[i].level[i].span += 1

        # 处理新节点的后退指针,这里上个节点就是 update[0],即为第一层索引的上个节点
        new_node.pre_node = update[0] if update[0] != self.head else None

        # 处理新节点的下个节点的前个节点指针
        if new_node.level[0].next:
            new_node.level[0].next.pre_node = new_node
        else:
            self.tail = new_node

        return new_node

    def delete(self, value: Any):
        pass

    def search(self, value: Any):
        pass

    def random_level(self):
        """
            生成新节点的层级
        """
        return 6  # TODO

    def create_node(self, level: int, value: Any):
        """
            生成一个新的节点
        """
        new = SkipListNode()
        new.level = [SkipListLevel() for _ in range(level)]
        new.value = value

        return new

    def insert_node(self, node: SkipListNode):
        pass

    def delete_node(self, node: SkipListNode):
        pass

    def search_node(self, value: Any):
        pass

    def update_node(self, node: SkipListNode, update: List[SkipListNode]):
        pass

    def delete_node(self, node: SkipListNode):
        pass
