#### 1005 K次取反后最大化的数组和
## 局部最优解: 把最小的负数变成正数
## 全局最优解: 使得数组和最大


# def largestSumAfterKNegations(nums, k) -> int:
#     ## 先将数组按绝对值从小到大排序
#     nums.sort(key = lambda x: abs(x))
#     ## 从大到小遍历数组
#     for i in range(len(nums)-1, 0, -1):
#         ## 如果当前数字小于0, 则将其变成正数
#         if nums[i] < 0 and k > 0:
#             nums[i] = -nums[i]
#             k -= 1
#     ## 如果k还大于0, 则继续处理
#     while k > 0:
#         ## 如果k是奇数, 则将数组中最小的数变成负数
#         if k % 2:
#             nums[0] = -nums[0]
#         ## 如果k是偶数, 则数组和不变
#         else:
#             break
#         k -= 1

#     return sum(nums)

# nums = [4,2,3]
# k = 1
# print(largestSumAfterKNegations(nums, k))  # 5

