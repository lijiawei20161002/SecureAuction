import time


p = 9223372036854775907
x1 = 7740074176276838879
x2 = 3010959959229715956
s = 1
c0 = 7600463858620182960
c1 = 139610317656655918
count = 0
start = time.time()
for i in range(p):
    if i == s:
        for j in range(p):
            if j == c0:
                for k in range(p):
                    break
end = time.time()
print(end-start)
