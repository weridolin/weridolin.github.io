#### 斐波那契数

# 1. 确定dp数组和实际下标代表的实际含义
# dp[i]表示第 输入为 i 时对应的费波切纳数值

# 2. 推导出表达式,因为下个状态是由上个状态决定的,所以一般为递归表达式
# dp[i] = dp[i-1]+dp[i-2]

# 3. dp数据初始化,即初始状态
# dp[0] = 0 dp[1] = 1

# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后

################  暴力循环 0(n)/O(n)   
# def fib(num:int):
#     res = [0]*(max(2,num))
#     res[0],res[1] = 0,1
#     for i in range(2,num):
#         res[i] = res[i-1]+ res[i-2]
#     return res[num-1]
# print(fib(5))


###############   暴力循环,只保存前2个 0(1)/O(n) 
# def fib(num:int):

#     pre,pre_pre = 1,0
#     if num == 1:return pre_pre
#     if num == 2:return pre
#     for i in range(2,num):
#         now = pre + pre_pre
#         pre,pre_pre = now,pre
#     return now
# print(fib(10))

############## 递归 0(n)/O(n/2) 
# def fib(num:int):
#     pre,pre_pre = 1,0
#     if num == 1:return pre_pre
#     if num == 2:return pre
#     for i in range(2,num):
#         now = pre + pre_pre
#         pre,pre_pre = now,pre
#     return now
# print(fib(10))


################ 假设你正在爬楼梯。需要 n 阶你才能到达楼顶。每次你可以爬 1 或 2 个台阶。
################  你有多少种不同的⽅法可以爬到楼顶呢？
################ 注意：给定 n 是⼀个正整数

# 1. 确定dp数组和实际下标代表的实际含义
# dp[i]表示第 台阶为 n 时，爬到楼顶的方法数

# 2. 假设 n = 8,因为每次可以只爬1/2个台阶,所以要么是 n-7时加1或者 n=6时加2，
# 既可以转换为 dp[8] = d[7]+d[6]
# ....
#  d[n] =d[n-1]+d[n-2]

# 3. dp数据初始化,即初始状态 n为正整数
#  dp[1] = 1 dp[2] = 2

# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后

### 代码参考 fib



#### 使用最小花费爬楼梯，唯一不同的是，这个是求最优价，上面是求全部解法
# 数组的每个下标作为⼀个阶梯，第 i 个阶梯对应着⼀个⾮负数的体⼒花费值 cost[i]（下标从 0 开始）。
# 直接理解为把爬上 i 个阶梯，就要花费 cost[i]值。那怕i是0
# 每当你爬上⼀个阶梯你都要花费对应的体⼒值，⼀旦⽀付了相应的体⼒值，你就可以选择向上爬⼀个阶
# 梯或者爬两个阶梯。
# 例如 [1,2,1,1,1,1] : 从数组第一个元素开始,每次可以为1/2步，到达数组尾部结束.

# 1. 确定dp数组和实际下标代表的实际含义
# dp[i]表示第i个台阶所花费的最小体力

# 2. 推导出表达式,到达第i个台阶依然由2中方式,为上个元素向后走1步或者上上个元素向后走2步.
# dp[i]表示到达第I个台阶的最小花费.所以dp[i]可以表示为：
# dp[i]=min(dp[i-1],dp[i-2])+cost[i] 
# 这里是求最小花费而不是总共花费，所以使用min

# 3. dp数据初始化,即初始状态
# dp[0]=cost[0],不走
# dp[1]=cost[1]  直接走一步
# dp[2]=min(dp[0],dp[1])+cost[2]  直接走2步

# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后 dp[i]=mim(dp[i-1],dp[i-2])+cost[i] 

# 5.数据验证
# 例子: [1, 100, 1, 1, 1, 100, 1, 1, 100, 1] ==> dp[]: [0, 1, 100, 2, 3, 3, 103, 4, 5, 104, 6]
# [1,0,0,1]

# def test(cost=[1, 100, 1, 1, 1, 100, 1, 1, 100, 1]):
#     dp = [0]*(len(cost)+1)
#     dp[0]=0 ##不走不给钱
#     dp[1]=min(cost[0],0) ## 2种可能.1是从1开始，2是从0开始向上爬1阶
#     dp[2]=min(cost[1]+dp[1],dp[0]+cost[0]) ##2种可能.1是从1开始爬1阶，2是从0开始向上爬2阶
#     # dp[3]=min(dp[1]+cost[1],dp[2]+cost[2]) ## 2种可能.1是从1开始向上爬2阶，2是从2开始向上爬1阶
#     for i in range(3,len(cost)+1): ## +1是因为消费完整个cost+1列表才到达楼顶
#         # 2种可能.1是从i-1开始向上爬1阶，2是从i-2开始向上爬2阶
#         dp[i]=min(dp[i-1]+cost[i-1],dp[i-2]+cost[i-2]) 
#     print(dp)
#     return dp[-1]

# print(test())

######### 最大子数组和
# 给你一个整数数组 nums ,请你找出一个具有最大和的连续子数组（子数组最少包含一个元素），返回其最大和。
# 子数组 是数组中的一个连续部分。

# 例子:
# 输入：nums = [-2,1,-3,4,-1,2,1,-5,4]
# 输出：6
# 解释：连续子数组 [4,-1,2,1] 的和最大,为6 


# 1. 确定dp数组和实际下标代表的实际含义
# dp[i]表示以i为结尾的整数数组的最大子串值
# dp[0]: nums[0]
# dp[1]: max(dp[0]+nums[1],nums[1]) [-2,1],[1]
# dp[2]: max(dp[1]+nums[2],nums[2]) [-2,1,-3],[1,-3],[-3] #

# 2. 推导出表达式,因为下个状态是由上个状态决定的,所以一般为递归表达式
# dp[i] = max(dp[i-1],dp[i-1]+num[i])

# 3. dp数据初始化,即初始状态
# dp[0]: nums[0]
# dp[1]: max(dp[0]+nums[1],nums[1]) [-2,1],[1]
# dp[2]:max(dp[1]+nums[2],nums[2]) [-2,1,-3],[1,-3],[-3])
# ...
# dp[i] =max(dp[i-1]+nums[i],nums[i])

# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后

# def get_max_child_array(nums = [-2,1,-3,4,-1,2,1,-5,4]):
#     if len(nums)==1:
#         return nums[0]
#     else:
#         pre_max = nums[0]
#         max_ = nums[0]
#         for index in range(1,len(nums)):
#             pre_max = max(nums[index],pre_max+nums[index])
#             max_ = max(pre_max,max_)   # 这里不是返回最后一个,而是取最大一个

#         return max_
# print(get_max_child_array(),get_max_child_array([1]),get_max_child_array([5,4,-1,7,8]))



######### 最大子数组乘积 #152

# 给你一个整数数组 nums ，请你找出数组中乘积最大的非空连续子数组（该子数组中至少包含一个数字），并返回该子数组所对应的乘积。
# 测试用例的答案是一个 32-位 整数。
# 子数组 是数组的连续子序列。


# 示例 1:

# 输入: nums = [2,3,-2,4]
# 输出: 6
# 解释: 子数组 [2,3] 有最大乘积 6。

# 示例 2:

# 输入: nums = [-2,0,-1]
# 输出: 0
# 解释: 结果不能为 2, 因为 [-2,-1] 不是子数组。


# 提示:

#     1 <= nums.length <= 2 * 104
#     -10 <= nums[i] <= 10
#     nums 的任何前缀或后缀的乘积都 保证 是一个 32-位 整数


# 1.确定DP数组及其下标代表的含义
## dp[i]表示前i个元素的子数组最大乘积

# 2. 推导出表达式,因为下个状态是由上个状态决定的,所以一般为递归表达式
# dp[i] = max(dp[i-1],dp[i-1]*num[i],num[i]) 
# 这里有一种情况，即为 dp[i-1]不一定是为 num[i-1]所有元素累乘,那么只有一种情情况，就是 dp[i-2] * num[i-1]变成了负数(同时即为最小值)，如果不为负数，那就应该是连续的。
# 所以应该加上 [num-1-i]的最小累乘值minValue
# dp[i] = max(dp[i-1],dp[i-1]*num[i],minValue*num[i],num[i]) 
# minValue[i]= TODO 最小乘积 

# 3. dp数据初始化,即初始状态
## dp[0]=nums[0]
## dp[1]=max[dp[0],dp[0]*nums[1],nums[i]]
## dp[2]=max[dp[1],dp[1]*nums[2],nums[2]]
# ...
# dp[i] =max(dp[i-1],dp[i-1]*nums[i],nums[i]) 

####


## 函数

def test(nums):
    if len(nums)==1:
        return nums[0]
    dp=[0]*(len(nums))
    dp[0]=nums[0]
    for i in range(1,len(nums)):
        if dp[i-1]*nums[i]<0:
            dp[i]=max(dp[i-1],nums[i])
        elif dp[i-1]*nums[i]>=0:
            dp[i]=max(dp[i-1],dp[i-1]*nums[i],nums[i])
    print(dp)
    return dp[-1]
print(test([-2,3,-4]))

# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后

##### 杨辉三角
# https://leetcode-cn.com/problems/pascals-triangle/
# 示例 1:

# 输入: numRows = 5
# 输出: [[1],[1,1],[1,2,1],[1,3,3,1],[1,4,6,4,1]]

# dp[i]表示第i层对应的数据，d[i][j]表示第i层第j个元素的值
# dp[0] = [[1]]
# dp[0][0] = 1
# dp[1] = [[1,1]]
# dp[1][0]=1,dp[1][1]=1
# dp[2] = [[1,2,1]] 
# dp[3] = [[1,3,3,1]] 
# dp[3][0] =1 dp[3][3] =1 dp[3][1]=dp[2][0]+dp[2][1] dp[3][2]=dp[2][1]+dp[2][2]
# ...


# 推导表达式
# dp[i][j] = dp[i-1][j-1]+d[i-1][j] i>2


# def pascals_triangle(numRows=5):
#     if numRows ==1:return [[1]]
#     if numRows ==2:return [[1],[1,1]]
#     dp = [[1],[1,1]]
#     for i in range(2,numRows):
#         tmp = [1]
#         for j in range(1,i):
#             tmp.append(dp[i-1][j-1]+dp[i-1][j])
#         tmp.append(1)
#         dp.append(tmp)
#     return dp
# print(pascals_triangle())

# def getRow(rowIndex):
#     """
#     :type rowIndex: int
#     :rtype: List[int]
#     """
#     if rowIndex ==0:return [[1]]
#     if rowIndex ==1:return [[1],[1,1]]
#     dp = [[1],[1,1]]
#     for i in range(2,rowIndex+1):
#         tmp = [1]
#         for j in range(1,i):
#             tmp.append(dp[i-1][j-1]+dp[i-1][j])
#         tmp.append(1)
#         dp.append(tmp)
#     return dp[-1]
# print(getRow(3))


#### 股票买卖问题
# 给定一个数组 prices ，它的第 i 个元素 prices[i] 表示一支给定股票第 i 天的价格。
# 你只能选择 某一天 买入这只股票，并选择在 未来的某一个不同的日子 卖出该股票。设计一个算法来计算你所能获取的最大利润。
# 返回你可以从这笔交易中获取的最大利润。如果你不能获取任何利润，返回 0 。

# 示例 1：

# 输入：[7,1,5,3,6,4]
# 输出：5
# 解释：在第 2 天（股票价格 = 1）的时候买入，在第 5 天（股票价格 = 6）的时候卖出，最大利润 = 6-1 = 5 。
#      注意利润不能是 7-1 = 6, 因为卖出价格需要大于买入价格；同时，你不能在买入前卖出股票。


# 1. 确定dp数组和实际下标代表的实际含义
# dp[i]表示以i天卖出可以获取的最大利润   minprice表示第I天最小的价格


# 2. 推导出表达式,因为下个状态是由上个状态决定的,所以一般为递归表达式
# dp[i] = max(dp[i-1],prices[i]-minprices)
# minprices = min(prices[i],minprice)

# 3. dp数据初始化,即初始状态,多了个最小状态方程
# dp[0]: 0 minprice = prices[0]
# dp[1]:max(dp[1],prices[1]-minprice))  minprice = min(prices[1],minprice)
# ...
# dp[i]:max(dp[i-1],prices[i]-minprice) minprice = min(prices[i],minprice)


# 4. 确定遍历顺序,比如当前状态是上次状态决定,则遍历顺序为从前到后
# 从前到后

# def maxProfit(prices=[7,1,5,3,6,4]):
#     """
#     :type prices: List[int]
#     :rtype: int
#     """
#     if len(prices)==1:return 0
#     dp = [0]*len(prices)
#     minprice = prices[0]
#     for i in range(1,len(prices)):
#         dp[i] = max(dp[i-1],prices[i]-minprice)
#         minprice = min(prices[i],minprice)
#     return max(dp,key=lambda item:item) 
# print(maxProfit())


#################### 路径相关 #############################
# ⼀个机器⼈位于⼀个 m x n ⽹格的左上⻆ （起始点在下图中标记为 “Start” ）。
# 机器⼈每次只能向下或者向右移动⼀步。机器⼈试图达到⽹格的右下⻆（在下图中标记为 “Finish” ）。
# 问总共有多少条不同的路径？
# 示例 2：
# 输⼊：m = 2, n = 3
# 输出：3
# 解释：
# 从左上⻆开始，总共有 3 条路径可以到达右下⻆。
# 1. 向右 -> 向右 -> 向下
# 2. 向右 -> 向下 -> 向右
# 3. 向下 -> 向右 -> 向右
# 示例 3：
# 输⼊：m = 7, n = 3
# 输出：28
# 示例 4：
# 输⼊：m = 3, n = 3
# 输出：6
# 提示：
# 1 <= m, n <= 100
# 题⽬数据保证答案⼩于等于 2 * 10^9

### 1 确定动态规划数据的含义
### dp[i][j]: 到第i，j个网关总共有多少条不同的路径


### 2 确定递推公式 
# 想要求dp[i][j]，只能有两个⽅向来推导出来，即dp[i - 1][j] 和 dp[i][j - 1]。
# 此时在回顾⼀下 dp[i - 1][j] 表示啥，是从(0, 0)的位置到(i - 1, j)有⼏条路径，dp[i][j - 1]同理。
# 那么很⾃然，dp[i][j] = dp[i - 1][j] + dp[i][j - 1]，因为dp[i][j]只有这两个⽅向过来。

### 3 确定初始条件
# d[i][0],d[0][j]都为 1 
#

### 4 确定遍历顺序
# d[i][j]都是从其上方和左方推到而来，只需要从左到右一层层遍历即可

### 5 举例
# 参考题目给的验证实例


# def pathCount(m,n):
#     dp = [[1 for i in range(n)] for i in range(m)]
#     for i in range(1,m):
#         for j in range(1,n):
#             dp[i][j]=dp[i-1][j]+dp[i][j-1]
#     return dp[m-1][n-1]


# print(pathCount(3,7))


################## 不同路径2


