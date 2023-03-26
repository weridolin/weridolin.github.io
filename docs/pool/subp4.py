from multiprocessing import shared_memory
import mmap
exist_share = shared_memory.SharedMemory(name="share")
import array

print(array.array('L', exist_share.buf[:12])) ## 
# print(exist_share.buf[:]