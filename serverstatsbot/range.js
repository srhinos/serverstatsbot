def createRange(length, min, max):
    max = max - min
    return [int(min + x*(max-min)/(length-1)) for x in range(length)]


total = 1000

def ranges():
    range_raw = [ 
        createRange(i[0], i[1], i[2]) for i in [
            [50, 0, 1000],
            [200, 1000, 10000],
            [750, 10000, 810000]
        ]   
    ]
    ranges = []
    for sublist in range_raw:
        ranges.extend(sublist)
    
    return ranges

