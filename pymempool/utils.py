def median(a):
    n = len(a)
    a.sort()

    if n % 2 == 0:
        median1 = a[n // 2]
        median2 = a[n // 2 - 1]
        median = (median1 + median2) / 2
    else:
        median = a[n // 2]
    return median
